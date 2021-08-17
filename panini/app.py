import os
import time
import asyncio
import uuid
import logging

from aiohttp import web

from panini.nats_client import NATSClient
from .managers import (
    _EventManager,
    _TaskManager,
    _IntervalTaskManager,
    _MiddlewareManager,
)
from .http_server.http_server_app import HTTPServer
from .exceptions import (
    InitializingEventManagerError,
    InitializingTaskError,
    InitializingIntervalTaskError,
)
from .middleware.error import ErrorMiddleware
from .utils.helper import (
    start_thread,
    get_app_root_path,
    create_client_code_by_hostname,
)
from .utils import logger

_app = None


class App(
    _EventManager, _TaskManager, _IntervalTaskManager, _MiddlewareManager, NATSClient
):
    def __init__(
        self,
        host: str,
        port: int,
        service_name: str = "panini_microservice_" + str(uuid.uuid4())[:10],
        client_id: str = None,
        tasks: list = None,
        reconnect: bool = False,
        max_reconnect_attempts: int = 60,
        reconnecting_time_sleep: int = 2,
        subscribe_subjects_and_callbacks: dict = None,
        allocation_queue_group: str = "",
        listen_subject_only_if_include: list = None,
        listen_subject_only_if_exclude: list = None,
        web_server: bool = False,
        web_app: web.Application = None,
        web_host: str = None,
        web_port: int = None,
        web_server_params: dict = {},
        logger_required: bool = True,
        logger_files_path: str = None,
        logger_in_separate_process: bool = False,
        pending_bytes_limit=65536 * 1024 * 10,
    ):
        """
        :param host: NATS broker host
        :param port: NATS broker port
        :param service_name: Name of microservice
        :param client_id: id of microservice, name and client_id used for NATS client name generating
        :param tasks: List of additional tasks
        :param reconnect: allows reconnect if connection to NATS has been lost
        :param max_reconnect_attempts: number of reconnect attempts
        :param reconnecting_time_sleep: pause between reconnection
        :param subscribe_subjects_and_callbacks: if you need to subscribe additional
                                        subjects(except subjects from event.py).
                                        This way doesn't support validators
        :param allocation_queue_group: name of NATS queue for distributing incoming messages among many NATS clients
                                    more detailed here: https://docs.nats.io/nats-concepts/queue
        :param listen_subject_only_if_include:   if not None, client will subscribe
                                                only to subjects that include these key words
        :param listen_subject_only_if_exclude:   if not None, client will not subscribe
                                                 to subjects that include these key words
        :param web_app: web.Application:       custom aiohttp app that you can create separately from panini.
                            if you set this argument client will only run this aiohttp app without handling
        :param web_host: Web application host
        :param web_port: Web application port
        :param logger_required: Is logger required for the project (if not - EmptyLogger will be provided)
        :param logger_files_path: main path for logs
        :param logger_in_separate_process: use log in the same or in different process
        """
        if subscribe_subjects_and_callbacks is None:
            subscribe_subjects_and_callbacks = {}
        if tasks is None:
            tasks = []
        try:
            if client_id is None:
                client_id = create_client_code_by_hostname(service_name)
            else:
                client_id = client_id
            os.environ["CLIENT_ID"] = client_id
            self.client_id = client_id
            self.service_name = service_name
            self.nats_config = {
                "host": host,
                "port": port,
                "client_id": client_id,
                "listen_subjects_callbacks": None,
                "allow_reconnect": reconnect,
                "queue": allocation_queue_group,
                "max_reconnect_attempts": max_reconnect_attempts,
                "reconnecting_time_wait": reconnecting_time_sleep,
                "pending_bytes_limit": pending_bytes_limit,
            }
            self.tasks = tasks
            self.listen_subject_only_if_include = listen_subject_only_if_include
            self.listen_subject_only_if_exclude = listen_subject_only_if_exclude
            assert (
                self.listen_subject_only_if_include is None
                or self.listen_subject_only_if_exclude is None
            ), "You can use only 1 of listen_subject_only_if_include/exclude at the same moment!"
            self.subscribe_subjects_and_callbacks = subscribe_subjects_and_callbacks

            self.app_root_path = get_app_root_path()

            self.logger_required = logger_required
            self.logger_in_separate_process = logger_in_separate_process

            # check, if TestClient is running
            if os.environ.get("PANINI_TEST_MODE"):
                self.logger_files_path = os.environ.get(
                    "PANINI_TEST_LOGGER_FILES_PATH", "test_logs"
                )
            else:
                self.logger_files_path = (
                    logger_files_path if logger_files_path else "logs"
                )
            self.logger = logger.Logger(None)

            if self.logger_required:
                self.set_logger(
                    self.service_name,
                    self.app_root_path,
                    self.logger_files_path,
                    False,
                    self.client_id,
                )

            self.logger_process = None
            self.log_stop_event = None
            self.log_listener_queue = None
            self.change_logger_config_listener_queue = None

            if web_server:
                self.http = web.RouteTableDef()  # for http decorator
                if web_app:
                    self.http_server = HTTPServer(base_app=self, web_app=web_app, web_server_params=web_server_params)
                else:
                    self.http_server = HTTPServer(
                        base_app=self, host=web_host, port=web_port, web_server_params=web_server_params,
                    )
            else:
                self.http_server = None
            global _app
            _app = self
        except InitializingEventManagerError as e:
            error = f"App.event_registrar critical error: {str(e)}"
            raise InitializingEventManagerError(error)

    # TODO: implement change logging configuration during runtime to make it work properly
    def change_log_config(self, new_formatters: dict, new_handlers: dict):
        self.change_logger_config_listener_queue.put(
            {"new_formatters": new_formatters, "new_handlers": new_handlers}
        )
        raise NotImplementedError

    def set_logger(
        self,
        service_name,
        app_root_path,
        logger_files_path,
        in_separate_process,
        client_id,
    ):
        if in_separate_process:
            (
                self.log_listener_queue,
                self.log_stop_event,
                self.logger_process,
                self.change_logger_config_listener_queue,
            ) = logger.set_logger(
                service_name,
                app_root_path,
                logger_files_path,
                in_separate_process,
                client_id,
            )
        else:
            logger.set_logger(
                service_name,
                app_root_path,
                logger_files_path,
                in_separate_process,
                client_id,
            )
        self.logger.logger = logging.getLogger(service_name)

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
                self.client_id,
            )

        try:
            subjects_and_callbacks = self.SUBSCRIPTIONS
            subjects_and_callbacks.update(self.subscribe_subjects_and_callbacks)
            if self.listen_subject_only_if_include is not None:
                for subject in subjects_and_callbacks.copy():
                    success = False
                    for subject_include in self.listen_subject_only_if_include:
                        if subject_include in subject:
                            success = True
                            break
                    if success is False:
                        del subjects_and_callbacks[subject]
            if self.listen_subject_only_if_exclude is not None:
                for subject in subjects_and_callbacks.copy():
                    success = True
                    for subject_exclude in self.listen_subject_only_if_exclude:
                        if subject_exclude in subject:
                            success = False
                            break
                    if success is False:
                        del subjects_and_callbacks[subject]
        except InitializingEventManagerError as e:
            error = f"App.event_registrar critical error: {str(e)}"
            raise InitializingEventManagerError(error)

        self.nats_config["listen_subjects_callbacks"] = subjects_and_callbacks
        NATSClient.__init__(self, **self.nats_config)
        asyncio.ensure_future(
            self.client.publish(
                f"panini_events.{self.service_name}.{self.client_id}.started",
                b"{}",
            )
        )

        self.tasks = self.tasks + self.TASKS
        self.interval_tasks = self.INTERVAL_TASKS

        self._start_tasks()

    def _start_tasks(self):
        loop = asyncio.get_event_loop()
        tasks = asyncio.all_tasks(loop)
        for coro in self.tasks:
            if not asyncio.iscoroutinefunction(coro):
                raise InitializingTaskError("Only coroutine tasks allowed")
            loop.create_task(coro())
        for interval in self.interval_tasks:
            for coro in self.interval_tasks[interval]:
                if not asyncio.iscoroutinefunction(coro):
                    raise InitializingIntervalTaskError(
                        "Only coroutine interval tasks allowed"
                    )
                loop.create_task(coro())
        if self.http_server:
            self.http_server.start_server()
        loop.run_until_complete(asyncio.gather(*tasks))


def get_app() -> App:
    return _app
