import os, sys
import time
import importlib
import venusian
import asyncio
import uuid
import logging
import random
from .nats_client.nats_client import NATSClient
from .logger.logger import Logger
from .managers import _EventManager, _TaskManager, _IntervalTaskManager
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
                 specific_app_directory: str = os.getcwd(),
                 max_reconnect_attempts: int = None,
                 reconnecting_time_sleep: int = 1,
                 app_strategy: str = 'asyncio',
                 num_of_queues: int = 1,    #only for sync strategy
                 subscribe_topics_and_callbacks: dict = {},
                 publish_topics: list = [],
                 allocation_quenue_group: str = "",
                 listen_topic_only_if_include: list = None,
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
            global _app
            _app = self
        except InitializingEventManagerError as e:
            error = f'App.event_registrator critical error: {str(e)}'
            raise InitializingEventManagerError(error)

    def start(self):
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
        self.start_tasks()

    def start_tasks(self):
        if self.app_strategy == 'asyncio':
            loop = asyncio.get_event_loop()
            tasks = asyncio.all_tasks(loop)
            for coro in self.tasks:
                if not asyncio.iscoroutinefunction(coro):
                    raise InitializingTaskError('For asyncio app_strategy only coroutine tasks allowed')
                loop.create_task(coro())
            for coro in self.interval_tasks:
                if not asyncio.iscoroutinefunction(coro):
                    raise InitializingIntevalTaskError('For asyncio app_strategy only coroutine interval tasks allowed')
                loop.create_task(coro())
            loop.run_until_complete(asyncio.gather(*tasks))
        elif self.app_strategy == 'sync':
            for t in self.tasks:
                if asyncio.iscoroutinefunction(t):
                    raise InitializingIntevalTaskError("For sync app_strategy coroutine task doesn't allowed")
                start_thread(t)
            for t in self.interval_tasks:
                if asyncio.iscoroutinefunction(t):
                    raise InitializingIntevalTaskError("For sync app_strategy coroutine interval_task doesn't allowed")
                start_thread(t)

    def _create_client_code_by_hostname(self, name):
        return '__'.join([
            name,
            os.environ['HOSTNAME'] if 'HOSTNAME' in os.environ else 'non_docker_env_' + str(random.randint(1, 1000000)),
            str(random.randint(1, 1000000))
        ])

    # def autodiscover2(self):
    #     module_name = os.getcwd().split('/')[-1]
    #     scanner = venusian.Scanner()
    #     try:
    #         module = importlib.import_module(module_name)
    #     except ModuleNotFoundError:
    #         raise ModuleNotFoundError(
    #             f'Unknown module {module_name}, {module_name}')
    #     scanner.scan(module)
    #
    # def autodiscover(self):
    #     entry_point = os.getcwd()
    #     all_module_paths = self._autodiscover_modules(os.getcwd())
    #     scanner = venusian.Scanner()
    #     def get_python_import_path(name, absolute_path):
    #         parent_directories = absolute_path.replace(''.join(['/' ,name, '.py']), '').replace(entry_point, '')
    #         if parent_directories != "" and parent_directories[0] == '/':
    #             parent_directories = parent_directories[1:]
    #         python_import_path = parent_directories.replace('/','.')
    #         if parent_directories == "":
    #             return name
    #         return '.'.join([python_import_path, name])
    #     for name, absolute_path in all_module_paths:
    #         path = get_python_import_path(name, absolute_path)
    #         print(path)
    #         try:
    #             module = importlib.import_module(path)
    #         except ModuleNotFoundError:
    #             raise ModuleNotFoundError(
    #                 f'Unknown module {name}, {absolute_path}')
    #         scanner.scan(module)
    #
    # def _autodiscover_modules(self, path):
    #     modules = []
    #     with os.scandir(path) as list_of_entries:
    #         for entry in list_of_entries:
    #             if entry.is_file() and entry.name[-3:] == '.py' and not entry.name == '__init__.py':
    #                 modules.append((entry.name[:-3], entry.__fspath__()))
    #             elif entry.is_dir() and not entry.name in ['bin', 'include', 'lib']:
    #                 modules = modules + self._autodiscover_modules("/".join([path, entry.name]))
    #     return modules
    #
    # def _path_import(self, absolute_path):
    #     spec = importlib.util.spec_from_file_location(absolute_path, absolute_path)
    #     module = importlib.util.module_from_spec(spec)
    #     spec.loader.exec_module(module)
    #     return module