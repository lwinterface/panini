import os, sys
import uuid
import logging
from nats_client.nats_client import NATSClient
from logger.logger import Logger

class App:
    def __init__(self,
                 host,
                 port,
                 service_name: str = 'anthill_microservice_'+str(uuid.uuid4())[:10],
                 client_id: str = str(uuid.uuid4())[:10],
                 reconnect: bool = False,
                 max_reconnect_attempts: int = None,
                 reconnecting_time_sleep: int = 1,
                 app_strategy: str = 'asyncio',
                 subscribe_topics_and_callbacks: dict = {},
                 publish_topics: list = [],
                 event_registrator_required: bool = True,
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
            if event_registrator_required:
                try:
                    mod = __import__(f'{service_name}.events', fromlist=['EventManager'])
                    registrator = getattr(mod, 'EventManager')
                    self.event_registrator = registrator()
                except Exception as e:
                    raise Exception(f'Import from events.py error: {e}')
                topics_and_callbacks = self.event_registrator.get_topics_and_callbacks()
                topics_and_callbacks.update(subscribe_topics_and_callbacks)
                if listen_topic_only_if_include is not None:
                    for topic in topics_and_callbacks.copy():
                        success = False
                        for topic_include in listen_topic_only_if_include:
                            if topic_include in topic:
                                success = True
                                break
                        if success is False:
                            del topics_and_callbacks[topic]
            else:
                topics_and_callbacks = {}

        except Exception as e:
            error = f'App.event_registrator critical error: {str(e)}'
            raise Exception(error)

        self.nats_client = NATSClient(
            client_id=client_id,
            host=host,
            port=port,
            listen_topics_callbacks=topics_and_callbacks,
            publish_topics=publish_topics,
            allow_reconnect=reconnect,
            queue=allocation_quenue_group,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnecting_time_wait=reconnecting_time_sleep,
            client_strategy=app_strategy
        )



