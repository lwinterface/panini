import os, sys
import time
import importlib
import threading
import venusian
import asyncio
import uuid
import logging
import random
from aiohttp import web
from .nats_client.nats_client import NATSClient
from .logger.logger import Logger
from .managers import _EventManager, _TaskManager, _IntervalTaskManager
from .http_server.http_server_app import HTTPServer
from .serializer import Serializer
from .exceptions import InitializingEventManagerError, InitializingTaskError, InitializingIntevalTaskError
from .utils.helper import start_thread

_app = None

class App(_EventManager, _TaskManager, _IntervalTaskManager, NATSClient):
    def __init__(self,
                 host,
                 port,
                 service_name: str = 'anthill_microservice_'+str(uuid.uuid4())[:10],
                 client_id: str = None,
                 tasks: list = [],
                 reconnect: bool = False,
                 max_reconnect_attempts: int = None,
                 reconnecting_time_sleep: int = 1,
                 app_strategy: str = 'asyncio',
                 num_of_queues: int = 1,    #only for sync strategy
                 subscribe_topics_and_callbacks: dict = {},
                 publish_topics: list = [],
                 allocation_quenue_group: str = "",
                 listen_topic_only_if_include: list = None,
                 web_app: web.Application = None,
                 web_host: str = None,
                 web_port: int = None,
                 logger_required: bool = True,
                 log_file: str = None,
                 log_formatter: str = '%(message)s',
                 console_level: str = logging.DEBUG,
                 file_level: str = logging.INFO,
                 logging_level: str = logging.INFO,
                 root_path: str = '',
                 ):
        """
        :param host: NATS broker host
        :param port: NATS broker port
        :param service_name: Name of microsirvice
        :param client_id: id of microservice, name and client_id used for NATS client name generating
        :param tasks:              #TODO
        :param start_tasks_now:    #TODO
        :param reconnect: allows reconnect if connection to NATS has been lost
        :param max_reconnect_attempts: any number
        :param reconnecting_time_sleep: pause between reconnection
        :param app_strategy: 'async' or 'sync' #TODO describe it more detailed
        :param subscribe_topics_and_callbacks: if you need to subscibe additional topics(except topics from event.py).
                                        This way doesn't support serializators
        :param publish_topics: REQUIRED ONLY FOR 'sync' app strategy. Skip it for 'asyncio' app strategy
        :param event_registrator_required: False if you don't want to register subscriptions
        :param allocation_quenue_group: name of NATS queue for distributing incoming messages among many NATS clients
                                    more detailed here: https://docs.nats.io/nats-concepts/queue
        :param listen_topic_only_if_include:   #TODO
        :param web_app: web.Application = None,
        :param web_host: str = None,    #TODO
        :param web_port: int = None,    #TODO
        :param logger_required:        #TODO
        :param log_file:               #TODO
        :param log_formatter:  #TODO
        :param console_level:  #TODO
        :param file_level:     #TODO
        :param logging_level:  #TODO
        :param root_path:      #TODO
        :param slack_webhook_url_for_logs:     #TODO
        :param telegram_token_for_logs:        #TODO
        :param telegram_chat_for_logs          #TODO
        """
        try:
            if client_id is None:
                client_id = self._create_client_code_by_hostname(service_name)
            else:
                client_id = client_id
            os.environ["CLIENT_ID"] = client_id
            self.nats_config = {
                'host':host,
                'port':port,
                'client_id':client_id,
                'listen_topics_callbacks':None,
                'publish_topics':publish_topics,
                'allow_reconnect':reconnect,
                'queue':allocation_quenue_group,
                'max_reconnect_attempts':max_reconnect_attempts,
                'reconnecting_time_wait':reconnecting_time_sleep,
                'client_strategy':app_strategy,
            }
            if app_strategy == 'sync':
                self.nats_config['num_of_queues'] = num_of_queues
            self.tasks = tasks
            self.app_strategy = app_strategy
            self.listen_topic_only_if_include = listen_topic_only_if_include
            self.subscribe_topics_and_callbacks = subscribe_topics_and_callbacks

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

            if web_app:
                self.http = web.RouteTableDef()     #for http decorator
                self.http_server = HTTPServer(base_app=self, web_app=web_app)
            elif web_host is not None or web_port is not None:
                self.http = web.RouteTableDef()     #for http decorator
                self.http_server = HTTPServer(base_app=self, host=web_host, port=web_port)
            else:
                self.http_server = None
            global _app
            _app = self
        except InitializingEventManagerError as e:
            error = f'App.event_registrator critical error: {str(e)}'
            raise InitializingEventManagerError(error)
        
    def start(self):
        if self.http_server is None:
            self._start()
        else:
            start_thread(self._start())
            
    def _start(self):
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
        except InitializingEventManagerError as e:
            error = f'App.event_registrator critical error: {str(e)}'
            raise InitializingEventManagerError(error)

        self.nats_config['listen_topics_callbacks'] = topics_and_callbacks

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
            if self.http_server:
                self.http_server.start_server()
            loop.run_until_complete(asyncio.gather(*tasks))
        elif self.app_strategy == 'sync':
            for task in self.tasks:
                if asyncio.iscoroutinefunction(task):
                    raise InitializingIntevalTaskError("For sync app_strategy coroutine task doesn't allowed")
                start_thread(task)
            for interval in self.interval_tasks:
                for task in self.interval_tasks[interval]:
                    if asyncio.iscoroutinefunction(task):
                        raise InitializingIntevalTaskError("For sync app_strategy coroutine interval_task doesn't allowed")
                    start_thread(task)
            if self.http_server:
                self.http_server.start_server()


    def _create_client_code_by_hostname(self, name: str):
        return '__'.join([
            name,
            os.environ['HOSTNAME'] if 'HOSTNAME' in os.environ else 'non_docker_env_' + str(random.randint(1, 1000000)),
            str(random.randint(1, 1000000))
        ])