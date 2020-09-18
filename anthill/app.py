import os, sys
import random
import importlib
import logging

from utils.singleton import singleton
from logger.logger import Logger
from messanger.msgr_client import MessengerClient
from .event_registrator import EventManager

class App:
    def __init__(self, **kwargs):
        #get base parameters
        self.service_name = kwargs.get('service_name', None)
        self.client_id = kwargs.get('client_id', str(random.randint(1,1000000)))
        os.environ['SERVICE_NAME'] = self.service_name
        os.environ['CLIENT_ID'] = self.client_id

        #logger
        self.log_file = kwargs.get('log_file', f'{self.service_name}.log')
        self.log_formatter = kwargs.get('log_formatter', '%(message)s')
        self.console_level = kwargs.get('console_level', logging.DEBUG)
        self.file_level = kwargs.get('file_level', logging.INFO)
        self.logging_level = kwargs.get('logging_level', logging.INFO)
        self.event_registrator_required = kwargs.get('event_registrator_required', True)
        script_position = os.path.dirname(sys.argv[0])
        self.root_path = kwargs.get('root_path', f'{script_position}/' if script_position else '')
        os.environ['SERVICE_ROOT_PATH'] = self.root_path
        self.slack_webhook_url = kwargs.get('slack_webhook_url', None)

        #msgr_client
        self.broker_host = kwargs.get('broker_host', None)
        self.port = kwargs.get('port', None)
        self.allow_reconnect = kwargs.get('allow_reconnect', None)
        self.max_reconnect_attempts = kwargs.get('max_reconnect_attempts', None)
        self.reconnecting_time_wait = kwargs.get('reconnecting_time_wait', None)
        self.if_error = kwargs.get('if_error', None)
        self.client_strategy = kwargs.get('client_strategy', 'in_current_process')
        self.topics_and_callbacks = kwargs.get('topics_and_callbacks', {})
        self.publish_topics = kwargs.get('publish_topics', [])
        self.queue = kwargs.get('queue', "")
        self.listen_topic_only_if_include_state = kwargs.get('listen_topic_only_if_include_state', False)
        self.listen_topic_only_if_include = kwargs.get('listen_topic_only_if_include', None)

    def initialize(self):
        self.logger = Logger(
            name=self.client_id,
            log_file=self.log_file,
            log_formatter=self.log_formatter,
            console_level=self.console_level,
            file_level=self.file_level,
            logging_level=self.logging_level,
            root_path=self.root_path,
            slack_webhook_url=self.slack_webhook_url
        )
        try:
            # event_registrator
            if self.event_registrator_required:
                mod = __import__(f'{self.service_name}.events', fromlist=['EventManager'])
                registrator = getattr(mod, 'EventManager')
                self.event_registrator = registrator()
                topics_and_callbacks = self.event_registrator.get_topics_and_callbacks()
                topics_and_callbacks.update(self.topics_and_callbacks)
                if self.listen_topic_only_if_include_state:
                    for topic in topics_and_callbacks.copy():
                        success = False
                        for topic_include in self.listen_topic_only_if_include:
                            if topic_include in topic:
                                success = True
                                break
                        if success is False:
                            del topics_and_callbacks[topic]
            else:
                topics_and_callbacks = {}

            self.logger.log(f"workbook: topics_and_callbacks({os.environ['CLIENT_ID']}): {list(topics_and_callbacks.keys())}")
        except Exception as e:
            error = f'WorkBook.event_registrator critical error: {str(e)}'
            self.logger.log(error, level='error')
            raise Exception(error)
        # msgr_client
        self.msgr_client = MessengerClient()
        connection = self.msgr_client.create_connection(
            client_id=self.client_id,
            broker_host=self.broker_host,
            port=self.port,
            listen_topics_callbacks=topics_and_callbacks,
            publish_topics=self.publish_topics,
            allow_reconnect=self.allow_reconnect,
            queue=self.queue,
            max_reconnect_attempts=self.max_reconnect_attempts,
            reconnecting_time_wait=self.reconnecting_time_wait,
            client_strategy=self.client_strategy
        )
        if not connection['success']:
            msg = 'MessengerClient connection problem: %s' % str(connection)
            self.logger.log(msg, level='error', slack=True)
            raise Exception(msg)



