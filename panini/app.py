import os
import time
import asyncio
import uuid
import logging
from aiohttp import web
from .nats_client.nats_client import NATSClient
from .managers import _EventManager, _TaskManager, _IntervalTaskManager
from .http_server.http_server_app import HTTPServer
from .exceptions import (
    InitializingEventManagerError,
    InitializingTaskError,
    InitializingIntervalTaskError,
)
from .utils.helper import (
    start_thread,
    get_app_root_path,
    create_client_code_by_hostname,
)
from .utils import logger

_app = None


class App(_EventManager, _TaskManager, _IntervalTaskManager, NATSClient):
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
        app_strategy: str = "asyncio",
        num_of_queues: int = 1,  # only for sync strategy
        subscribe_subjects_and_callbacks: dict = None,
        publish_subjects: list = None,
        allocation_queue_group: str = "",
        listen_subject_only_if_include: list = None,
        web_server: bool = False,
        web_app: web.Application = None,
        web_host: str = None,
        web_port: int = None,
        logger_required: bool = True,
        logger_files_path: str = None,
        logger_in_separate_process: bool = False,
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
        :param app_strategy: 'async' or 'sync'. We strongly recommend using 'async'.
        'sync' app_strategy works in many times slower and created only for lazy microservices.
        :param subscribe_subjects_and_callbacks: if you need to subscribe additional
                                        subjects(except subjects from event.py).
                                        This way doesn't support validators
        :param publish_subjects: REQUIRED ONLY FOR 'sync' app strategy. Skip it for 'asyncio' app strategy
        :param allocation_queue_group: name of NATS queue for distributing incoming messages among many NATS clients
                                    more detailed here: https://docs.nats.io/nats-concepts/queue
        :param listen_subject_only_if_include:   if not None, client will subscribe
                                                only to subjects that include these key words
        :param web_app: web.Application:       custom aiohttp app that you can create separately from panini.
                            if you set this argument client will only run this aiohttp app without handling
        :param web_host: Web application host
        :param web_port: Web application port
        :param logger_required: Is logger required for the project (if not - EmptyLogger will be provided)
        :param logger_files_path: main path for logs
        :param logger_in_separate_process: use log in the same or in different process
        """
        if publish_subjects is None:
            publish_subjects = []
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
            self._client_id = client_id
            self.service_name = service_name
            self.nats_config = {
                "host": host,
                "port": port,
                "client_id": client_id,
                "listen_subjects_callbacks": None,
                "publish_subjects": publish_subjects,
                "allow_reconnect": reconnect,
                "queue": allocation_queue_group,
                "max_reconnect_attempts": max_reconnect_attempts,
                "reconnecting_time_wait": reconnecting_time_sleep,
                "client_strategy": app_strategy,
            }
            if app_strategy == "sync":
                self.nats_config["num_of_queues"] = num_of_queues
            self.tasks = tasks
            self.app_strategy = app_strategy
            self.listen_subject_only_if_include = listen_subject_only_if_include
            self.subscribe_subjects_and_callbacks = subscribe_subjects_and_callbacks

            self.app_root_path = get_app_root_path()

            self.logger_required = logger_required
            self.logger_in_separate_process = logger_in_separate_process
            self.logger_files_path = logger_files_path if logger_files_path else "logs"
            self.logger = logger.Logger(None)
            self.logger_process = None
            self.log_stop_event = None
            self.log_listener_queue = None
            self.change_logger_config_listener_queue = None

            if web_server:
                self.http = web.RouteTableDef()  # for http decorator
                if web_app:
                    self.http_server = HTTPServer(base_app=self, web_app=web_app)
                else:
                    self.http_server = HTTPServer(
                        base_app=self, host=web_host, port=web_port
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
        if self.http_server:
            self._start()
        else:
            start_thread(self._start())

    def _start(self):
        if self.logger_required:
            self.set_logger(
                self.service_name,
                self.app_root_path,
                self.logger_files_path,
                self.logger_in_separate_process,
                self._client_id,
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
        except InitializingEventManagerError as e:
            error = f"App.event_registrar critical error: {str(e)}"
            raise InitializingEventManagerError(error)

        self.nats_config["listen_subjects_callbacks"] = subjects_and_callbacks

        NATSClient.__init__(self, **self.nats_config)

        self.tasks = self.tasks + self.TASKS
        self.interval_tasks = self.INTERVAL_TASKS
        self._start_tasks()

    def _start_tasks(self):
        if self.app_strategy == "asyncio":
            loop = asyncio.get_event_loop()
            tasks = asyncio.all_tasks(loop)
            for coro in self.tasks:
                if not asyncio.iscoroutinefunction(coro):
                    raise InitializingTaskError(
                        "For asyncio app_strategy only coroutine tasks allowed"
                    )
                loop.create_task(coro())
            for interval in self.interval_tasks:
                for coro in self.interval_tasks[interval]:
                    if not asyncio.iscoroutinefunction(coro):
                        raise InitializingIntervalTaskError(
                            "For asyncio app_strategy only coroutine interval tasks allowed"
                        )
                    loop.create_task(coro())
            if self.http_server:
                self.http_server.start_server()
            loop.run_until_complete(asyncio.gather(*tasks))
        elif self.app_strategy == "sync":
            time.sleep(1)
            for task in self.tasks:
                if asyncio.iscoroutinefunction(task):
                    raise InitializingIntervalTaskError(
                        "For sync app_strategy coroutine task doesn't allowed"
                    )
                start_thread(task)
            for interval in self.interval_tasks:
                for task in self.interval_tasks[interval]:
                    if asyncio.iscoroutinefunction(task):
                        raise InitializingIntervalTaskError(
                            "For sync app_strategy coroutine interval_task doesn't allowed"
                        )
                    start_thread(task)
            if self.http_server:
                self.http_server.start_server()
