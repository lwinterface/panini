import os, sys
import uuid
from messanger.msgr_client import MessengerClient

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
                 listen_topic_only_if_include: list = None
                 ):
        """
        host: NATS broker host
        port: NATS broker port
        service_name: Name of microsirvice
        client_id: id of microservice, name and client_id used for NATS client name generating
        reconnect: allows reconnect if connection to NATS has been lost
        max_reconnect_attempts: any number
        reconnecting_time_sleep: pause between reconnection
        app_strategy: 'async' or 'sync' #TODO describe it more detailed
        subscribe_topics_and_callbacks: if you need to subscibe additional topics(except topics from event.py).
                                        This way doesn't support serializators
        publish_topics: REQUIRED ONLY FOR 'sync' app strategy. Skip it for 'asyncio' app strategy
        event_registrator_required: False if you don't want to register subscriptions
        allocation_quenue_group: name of NATS queue for distributing incoming messages among many NATS clients
                                    more detailed here: https://docs.nats.io/nats-concepts/queue

        """
        try:
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

        self.nats_client = MessengerClient()
        connection = self.nats_client.create_connection(
            client_id=client_id,
            broker_host=host,
            port=port,
            listen_topics_callbacks=topics_and_callbacks,
            publish_topics=publish_topics,
            allow_reconnect=reconnect,
            queue=allocation_quenue_group,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnecting_time_wait=reconnecting_time_sleep,
            client_strategy=app_strategy
        )
        if not connection['success']:
            msg = 'NATSClient connection problem: %s' % str(connection)
            raise Exception(msg)



