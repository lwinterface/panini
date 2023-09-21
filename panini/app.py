import asyncio
import logging
import os
import uuid
from types import FunctionType
from typing import Optional, Callable

from nats.js import api

from panini.managers.nats_client import NATSClient
from .exceptions import InitializingEventManagerError

from .managers.event_manager import EventManager, Listen
from .managers.task_manager import TaskManager
from .middleware.error import ErrorMiddleware
from .utils import logger
from .utils.helper import (
    get_app_root_path,
    create_client_code_by_hostname,
)

_app = None


class App:
    def __init__(
            self,
            host: str = None,
            port: int or str = None,
            service_name: str = "panini_microservice_" + str(uuid.uuid4())[:10],
            servers: list = None,
            client_nats_name: str = None,
            reconnect: bool = False,
            max_reconnect_attempts: int = 60,
            reconnecting_time_sleep: int = 2,
            allocation_queue_group: str = "",
            logger_required: bool = True,
            logger_files_path: str = None,
            logger_in_separate_process: bool = False,
            custom_logger: logging.Logger = None,
            pending_bytes_limit=65536 * 1024 * 10,
            ignore_tasks_exceptions: bool = True,
            **kwargs
    ):
        """
        :param host: NATS broker host
        :param port: NATS broker port
        :param service_name: Name of microservice
        :param servers: Alternative to NATS broker host+NATS broker port. Allowed establish connection
        to multiple NATS brokers
        :param client_id: id of microservice, name and client_id used for NATS client name generating
        :param reconnect: allows reconnect if connection to NATS has been lost
        :param max_reconnect_attempts: number of reconnect attempts
        :param reconnecting_time_sleep: pause between reconnection
        :param allocation_queue_group: name of NATS queue for distributing incoming messages among many NATS clients
                                    more detailed here: https://docs.nats.io/nats-concepts/queue
        :param logger_required: Is logger required for the project (if not - EmptyLogger will be provided)
        :param logger_files_path: main path for logs
        :param logger_in_separate_process: use log in the same or in different process
        """

        try:
            if client_nats_name is None:
                self.client_nats_name = create_client_code_by_hostname(service_name)
            else:
                self.client_nats_name = client_nats_name
            os.environ["CLIENT_NATS_NAME"] = self.client_nats_name

            self.loop = asyncio.get_event_loop()

            self.service_name = service_name

            self._event_manager = EventManager()
            self._task_manager = TaskManager()
            self.nats = NATSClient(
                host=host,
                port=port,
                servers=servers,
                client_nats_name=self.client_nats_name,
                loop=self.loop,
                allow_reconnect=reconnect,
                queue=allocation_queue_group,
                max_reconnect_attempts=max_reconnect_attempts,
                reconnecting_time_wait=reconnecting_time_sleep,
                pending_bytes_limit=pending_bytes_limit,
                **kwargs
            )

            self.app_root_path = get_app_root_path()
            self.logger_required = logger_required
            self.logger_in_separate_process = logger_in_separate_process

            self._ignore_tasks_exceptions = ignore_tasks_exceptions

            # check, if TestClient is running
            if os.environ.get("PANINI_TEST_MODE"):
                self.logger_files_path = os.environ.get(
                    "PANINI_TEST_LOGGER_FILES_PATH", "test_logs"
                )
            else:
                self.logger_files_path = (
                    logger_files_path if logger_files_path else "logs"
                )

            if custom_logger:
                self.logger = custom_logger
            elif self.logger_required:
                self.logger = logger.Logger(None)
                self.set_logger(
                    self.service_name,
                    self.app_root_path,
                    self.logger_files_path,
                    False,
                    self.client_nats_name,
                )
            else:
                self.logger = None

            self.logger_process = None
            self.log_stop_event = None
            self.log_listener_queue = None
            self.change_logger_config_listener_queue = None

            self.http_server = None
            self.http = None

            self.on_start_task = self._task_manager.register_on_start_task
            self.task = self._task_manager.register_task
            self.timer_task = self._task_manager.register_interval_task

            global _app
            _app = self

        except InitializingEventManagerError as e:
            error = f"App.event_registrar critical error: {str(e)}"
            raise InitializingEventManagerError(error)

    def setup_web_server(self, host=None, port=None, web_app=None, params: dict = None, middlewares: list = None):
        """
        Setup server and run with NATS when called app.start()
        """
        from aiohttp import web
        from .http_server.http_server_app import HTTPServer

        self.http = web.RouteTableDef()  # for http decorator
        if web_app:
            self.http_server = HTTPServer(
                routes=self.http,
                loop=self.loop,
                web_app=web_app,
                web_server_params=params,
                middlewares=middlewares
            )
        else:
            self.http_server = HTTPServer(
                routes=self.http,
                loop=self.loop,
                host=host,
                port=port,
                web_server_params=params,
                middlewares=middlewares
            )

    def add_filters(self, include: list = None, exclude: list = None):
        """
        Allows to listen subject only if subject include or exclude string from lists in agrs
        """
        return self.nats.add_filters(include, exclude)

    def set_logger(
            self,
            service_name,
            app_root_path,
            logger_files_path,
            in_separate_process,
            client_nats_name,
    ):
        if in_separate_process:
            (
                self.log_listener_queue,
                self.log_stop_event,
                self.logger_process
            ) = logger.set_logger(
                service_name,
                app_root_path,
                logger_files_path,
                in_separate_process,
                client_nats_name,
            )
        else:
            logger.set_logger(
                service_name,
                app_root_path,
                logger_files_path,
                in_separate_process,
                client_nats_name,
            )
        self.logger.logger = logging.getLogger(service_name)

    def listen(
            self,
            subject: list or str,
            data_type=dict,
            **kwargs
    ):
        return self._event_manager.listen(
            subject=subject,
            data_type=data_type,
            **kwargs
        )

    def js_listen(
            self,
            subject: str = None,
            data_type=dict,
            queue: str = None,
            durable: Optional[str] = None,
            stream: Optional[str] = None,
            config: Optional[api.ConsumerConfig] = None,
            manual_ack: Optional[bool] = False,
            ordered_consumer: Optional[bool] = False,
            idle_heartbeat: Optional[float] = None,
            flow_control: Optional[bool] = False,
            **kwargs
    ):
        """
        "PUSH" JetStream listen(subscribe)

        :param subject: Subject from a stream from JetStream.
        :param data_type: Type of message to convert to.
        :param queue: Deliver group name from a set a of queue subscribers.
        :param durable: Name of the durable consumer to which the the subscription should be bound.
        :param stream: Name of the stream to which the subscription should be bound. If not set,
          then the client will automatically look it up based on the subject.
        :param config: api.ConsumerConfig object of JetStream, represent consumer configuration
        :param manual_ack: Disables auto acking for async subscriptions.
        :param ordered_consumer: Enable ordered consumer mode.
        :param idle_heartbeat: Enable Heartbeats for a consumer to detect failures.
        :param flow_control: Enable Flow Control for a consumer.
        """
        return self._event_manager.js_listen(
            subject=subject,
            data_type=data_type,
            queue=queue,
            durable=durable,
            stream=stream,
            config=config,
            manual_ack=manual_ack,
            ordered_consumer=ordered_consumer,
            idle_heartbeat=idle_heartbeat,
            flow_control=flow_control,
            **kwargs
        )

    async def publish(
            self,
            subject: str,
            message,
            reply_to: str = "",
            force: bool = False,
            headers: dict = None,
            *args,
            **kwargs
    ):
        return await self.nats.publish(
            subject=subject,
            message=message,
            reply_to=reply_to,
            force=force,
            headers=headers,
            *args,
            **kwargs
        )

    def publish_sync(
            self,
            subject: str,
            message,
            reply_to: str = "",
            force: bool = False,
            headers: dict = None,
            *args,
            **kwargs
    ):
        return self.nats.publish_sync(
            subject=subject,
            message=message,
            reply_to=reply_to,
            force=force,
            headers=headers,
            *args,
            **kwargs
        )

    async def request(
            self,
            subject: str,
            message,
            timeout: int = 10,
            response_data_type: type = dict,
            headers: dict = None,
            *args,
            **kwargs
    ):
        return await self.nats.request(
            subject=subject,
            message=message,
            timeout=timeout,
            response_data_type=response_data_type,
            headers=headers,
            *args,
            **kwargs
        )

    def request_sync(
            self,
            subject: str,
            message,
            timeout: int = 10,
            response_data_type: type = dict,
            headers: dict = None,
            *args,
            **kwargs
    ):
        return self.nats.request_sync(
            subject=subject,
            message=message,
            timeout=timeout,
            response_data_type=response_data_type,
            headers=headers,
            *args,
            **kwargs
        )

    async def publish_js(
            self,
            subject: str,
            message,
            timeout: float = None,
            stream: str = None,
            headers: dict = None,
            *args,
            **kwargs
    ):
        return await self.nats.publish_js(
            subject=subject,
            message=message,
            timeout=timeout,
            stream=stream,
            headers=headers,
            *args,
            **kwargs
        )

    def subscribe_new_subject_sync(
            self,
            subject: str,
            callback: Callable,
            data_type=dict,
            queue="",
            **listen_kwargs
    ):
        return self.nats.subscribe_new_subject_sync(
            listener=Listen(
                callback=callback,
                subject=subject,
                data_type=data_type,
                queue=queue,
                _meta=listen_kwargs
            )
        )

    async def subscribe_new_subject(
            self,
            subject: str,
            callback: Callable,
            data_type=dict,
            queue="",
            **listen_kwargs
    ):
        return await self.nats.subscribe_new_subject(
            listener=Listen(
                callback=callback,
                subject=subject,
                data_type=data_type,
                queue=queue,
                _meta=listen_kwargs
            ),
        )

    def unsubscribe_subject_sync(self, subject: str):
        return self.nats.unsubscribe_subject_sync(subject)

    async def unsubscribe_subject(self, subject: str):
        return await self.nats.unsubscribe_subject(subject)

    def add_middleware(self, cls, *args, **kwargs):
        return self.nats.middleware_manager.add_middleware(cls, *args, **kwargs)

    def _start_event(self):
        asyncio.ensure_future(
            self.nats._publish(
                f"panini_events.{self.service_name}.{self.client_nats_name}.started",
                b"{}",
                force=True
            )
        )

    def start(self):
        if (
                os.environ.get("PANINI_TEST_MODE")
                and os.environ.get("PANINI_TEST_MODE_USE_ERROR_MIDDLEWARE", "false")
                == "true"
        ):
            def exception_handler(e, **kwargs):
                self.logger.exception(f"Error: {e}, for kwargs: {kwargs}")
                raise

            self.add_middleware(
                ErrorMiddleware, error=Exception, callback=exception_handler
            )
        if self.logger_required and self.logger_in_separate_process:
            self.set_logger(
                self.service_name,
                self.app_root_path,
                self.logger_files_path,
                True,
                self.client_nats_name,
            )

        self.nats.set_listeners(
            self._event_manager.subscriptions,
            self._event_manager.js_subscriptions,
        )
        # establish NATS connection
        self.nats.start()
        if self.nats.enable_js:
            self.js = self.nats.js

        # run on_start tasks
        loop = asyncio.get_event_loop()
        for on_start in self._task_manager._on_start_tasks:
            loop.run_until_complete(on_start())

        # subscribe all listeners
        loop.run_until_complete(self.nats.subscribe_listeners())
        self.nats.print_connect()

        # send first message
        self._start_event()

        # prepare all tasks from task_manager
        self._task_manager.create_tasks()
        tasks = asyncio.all_tasks(loop)

        # start app, with http_server if required
        if self.http_server:
            self.http_server.start_server()
        else:
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=self._ignore_tasks_exceptions))




def get_app() -> App:
    return _app
