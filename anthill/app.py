import os
import time
import asyncio
import uuid
import logging
import random
import argparse
from aiohttp import web

from .emulator.storage_handler import StorageHandler
from .nats_client.nats_client import NATSClient
from .logger.logger import Logger
from .managers import _EventManager, _TaskManager, _IntervalTaskManager
from .http_server.http_server_app import HTTPServer
from .exceptions import InitializingEventManagerError, InitializingTaskError, InitializingIntevalTaskError
from .utils.helper import start_thread, start_process

_app = None


class App(_EventManager, _TaskManager, _IntervalTaskManager, NATSClient):
    def __init__(self,
                 host,
                 port,
                 service_name: str = 'anthill_microservice_'+str(uuid.uuid4())[:10],
                 client_id: str = None,
                 tasks: list = [],
                 reconnect: bool = False,
                 max_reconnect_attempts: int = 60,
                 reconnecting_time_sleep: int = 2,
                 app_strategy: str = 'asyncio',
                 num_of_queues: int = 1,    #only for sync strategy
                 subscribe_topics_and_callbacks: dict = {},
                 publish_topics: list = [],
                 allocation_quenue_group: str = "",
                 listen_topic_only_if_include: list = None,
                 web_server=False,
                 web_app = None,
                 web_host: str = None,
                 web_port: int = None,
                 web_framework: str = None,
                 logger_required: bool = True,
                 log_file: str = None,
                 log_formatter: str = '%(message)s',
                 console_level: int = logging.DEBUG,
                 file_level: int = logging.INFO,
                 logging_level: int = logging.INFO,
                 root_path: str = '',
                 store: bool = False
                 ):
        """
        :param host: NATS broker host
        :param port: NATS broker port
        :param service_name: Name of microsirvice
        :param client_id: id of microservice, name and client_id used for NATS client name generating
        :param tasks:              List of additional tasks
        :param reconnect: allows reconnect if connection to NATS has been lost
        :param max_reconnect_attempts:  number of reconnect attempts
        :param reconnecting_time_sleep: pause between reconnection
        :param app_strategy: 'async' or 'sync'. We strongly recommend using 'async'.
        'sync' app_strategy works in many times slower and created only for lazy microservices.
        :param subscribe_topics_and_callbacks: if you need to subscibe additional topics(except topics from event.py).
                                        This way doesn't support serializators
        :param publish_topics: REQUIRED ONLY FOR 'sync' app strategy. Skip it for 'asyncio' app strategy
        :param event_registrator_required: False if you don't want to register subscriptions
        :param allocation_quenue_group: name of NATS queue for distributing incoming messages among many NATS clients
                                    more detailed here: https://docs.nats.io/nats-concepts/queue
        :param listen_topic_only_if_include:   if not None, client will subscribe only to topics that include these key words
        :param web_app: web.Application:       custom aiohttp app that you can create separately from anthill.
                            if you set this argument client will only run this aiohttp app without handeling
        :param web_host: str = None,    #TODO
        :param web_port: int = None,    #TODO
        :param logger_required:        #TODO
        :param log_file:               #TODO
        :param log_formatter:  #TODO
        :param console_level:  #TODO
        :param file_level:     #TODO
        :param logging_level:  #TODO
        :param root_path:      #TODO
        :param data_absorbing: if True microservice sends in the background events initiated from outside and inside to
                            absorber. Also it sends dynamic variables user set in order to represent the state
                            of microservice. Absorber takes all this data and stores it in ArcticDB
        :param data_absorbing_frequency: mean how often it will send data. For example data_absorbing_frequency=30
                            means send data each 30 seconds
        """
        try:
            if client_id is None:
                client_id = self._create_client_code_by_hostname(service_name)
            else:
                client_id = client_id
            os.environ["CLIENT_ID"] = client_id
            self.run_mode, work_session, start_timestamp = self._get_runmode_from_arguments()
            self.store = store
            self.client_id = client_id
            self.service_name = service_name
            if self.run_mode == 'main_mode' and self.store:
                # self.data_absorbing_config = {
                #     'client_id':client_id,
                #     'num_executors':data_absorbing_num_executors,
                #     'nats_host': host,
                #     'nats_port': port,
                # }
                pass
            elif self.run_mode == 'backtest':
                self.topic_prefix = '.'.join(['reproducer',client_id])
                # TODO: run reproducer
                # TODO: change topics to reproducer's topics with client_id
                # TODO: upload state
                # TODO: put state
                # TODO: send start message when microservice ready
                pass

            self.nats_config = {
                'host': host,
                'port': port,
                'client_id': client_id,
                'listen_topics_callbacks': None,
                'publish_topics': publish_topics,
                'allow_reconnect': reconnect,
                'queue': allocation_quenue_group,
                'max_reconnect_attempts': max_reconnect_attempts,
                'reconnecting_time_wait': reconnecting_time_sleep,
                'client_strategy': app_strategy,
                'store': store,
            }
            if app_strategy == 'sync':
                self.nats_config['num_of_queues'] = num_of_queues
            self.tasks = tasks
            self.app_strategy = app_strategy
            self.listen_topic_only_if_include = listen_topic_only_if_include
            self.subscribe_topics_and_callbacks = subscribe_topics_and_callbacks
            self.web_framework = web_framework
            if logger_required:
                self.logger = Logger(
                    name=client_id,
                    log_file=log_file if log_file else service_name+'.log',
                    log_formatter=log_formatter,
                    console_level=console_level,
                    file_level=file_level,
                    logging_level=logging_level,
                    root_path=root_path,
                )
            else:
                self.logger = lambda *x: Exception("Logger hasn't been connected")
            if web_server:
                if self.web_framework == 'aiohttp':
                    self.http = web.RouteTableDef()  # for http decorator
                    if web_app:
                        self.http_server = HTTPServer(base_app=self, web_app=web_app, web_framework=web_framework)
                    else:
                        self.http_server = HTTPServer(base_app=self, host=web_host, port=web_port, web_framework=web_framework)
                elif self.web_framework == 'fastapi':
                    # start_thread(self._start())
                    if web_app:
                        self.http_server = HTTPServer(base_app=self, web_app=web_app, web_framework=web_framework)
                    else:
                        self.http_server = HTTPServer(base_app=self, host=web_host, port=web_port, web_framework=web_framework)
                    self.http = self.http_server.web_app
            else:
                self.http_server = None
            global _app
            _app = self
        except InitializingEventManagerError as e:
            error = f'App.event_registrator critical error: {str(e)}'
            raise InitializingEventManagerError(error)

    def _get_runmode_from_arguments(self):
        parser = argparse.ArgumentParser(description='Run microservice\nUsage: python [module name] [mode] [timestamp]')
        parser.add_argument('args', type=str, nargs='*')
        args = parser.parse_args().args
        if args == []:
            return 'main_mode', None, None
        elif not args[0] == 'backtest':
            raise Exception(f'Unexpected arguments: {args}')
        elif len(args) == 1:
            return args[0], None, None
        elif args[1] == 'list':
            # TODO: request list of worksessions; print it, stop system
            pass
        elif len(args) == 2:
            return args[0], args[1], None
        elif len(args) == 3:
            return args
        else:
            raise Exception(f'Too many arguments: {args}')

    def start(self, uvicorn_app_target: str = None):
        print('start')
        if self.store:
            start_process(StorageHandler(self.client_id, self.service_name, "storage_queue").run)
        # if self.run_mode == 'main_mode' and self.data_absorbing:
        #     run_absorber(**self.data_absorbing_config)
        if self.http_server is None:
            self._start()
        elif self.web_framework == 'fastapi':
            self.http_server.start_server(uvicorn_app_target)
            with self.http_server.server.run_in_thread():
                self._start()
        else:
            start_thread(self._start())



            
    def _start(self):
        print('_start')
        try:
            topics_and_callbacks = self.SUBSCRIPTIONS
            topics_and_callbacks.update(self.subscribe_topics_and_callbacks)
            if self.listen_topic_only_if_include is not None:
                for topic in topics_and_callbacks.copy():
                    success = False
                    for topic_include in self.listen_topic_only_if_include:
                        if topic_include in topic:
                            success = True
                            break
                    if success is False:
                        del topics_and_callbacks[topic]
            self.topics_and_callbacks = topics_and_callbacks
        except InitializingEventManagerError as e:
            error = f'App.event_registrator critical error: {str(e)}'
            raise InitializingEventManagerError(error)

        self.nats_config['listen_topics_callbacks'] = topics_and_callbacks
        self.connector = None
        print("init nats")
        NATSClient.__init__(self,
            **self.nats_config
        )
        self.tasks = self.tasks + self.TASKS
        self.interval_tasks = self.INTERVAL_TASKS
        self._start_tasks()

    def _start_tasks(self):
        if self.app_strategy == 'asyncio':
            loop = asyncio.get_event_loop()
            tasks = asyncio.all_tasks(loop)
            for coro in self.tasks:
                if not asyncio.iscoroutinefunction(coro):
                    raise InitializingTaskError('For asyncio app_strategy only coroutine tasks allowed')
                loop.create_task(coro())
            for interval in self.interval_tasks:
                for coro in self.interval_tasks[interval]:
                    if not asyncio.iscoroutinefunction(coro):
                        raise InitializingIntevalTaskError('For asyncio app_strategy only coroutine interval tasks allowed')
                    loop.create_task(coro())
            if self.web_framework == 'aiohttp':
                self.http_server.start_server()
            loop.run_until_complete(asyncio.gather(*tasks))
        elif self.app_strategy == 'sync':
            time.sleep(1)
            for task in self.tasks:
                if asyncio.iscoroutinefunction(task):
                    raise InitializingIntevalTaskError("For sync app_strategy coroutine task doesn't allowed")
                start_thread(task)
            for interval in self.interval_tasks:
                for task in self.interval_tasks[interval]:
                    if asyncio.iscoroutinefunction(task):
                        raise InitializingIntevalTaskError("For sync app_strategy coroutine interval_task doesn't allowed")
                    start_thread(task)
            if self.web_framework == 'aiohttp':
                self.http_server.start_server()

    def _create_client_code_by_hostname(self, name: str):
        return '__'.join([
            name,
            os.environ['HOSTNAME'] if 'HOSTNAME' in os.environ else 'non_docker_env_' + str(random.randint(1, 1000000)),
            str(random.randint(1, 1000000))
        ])