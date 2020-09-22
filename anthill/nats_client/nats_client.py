import sys
import time
import random

from utils.helper import start_thread
from logger.logger import Logger, InterServicesRequestLogger
from utils.singleton import singleton
import config.msgr_config as config


class NATSClient:

    def __init__(self,
                client_id: str,
                host: str,
                port: int,
                listen_topics_callbacks: dict,
                allow_reconnect: bool or None,
                max_reconnect_attempts: int or None,
                reconnecting_time_wait: int or None,
                if_error='warning',  # warning or error
                publish_topics=[],
                # TODO: auth_credentialns
                queue="",
                client_strategy='in_current_process',  # in_current_process' or in_separate_processes'
                pending_bytes_limit=65536 * 1024 * 10,
                ):
        """
        :param client_id: instance identificator for NATS, str
        :param broker_ip: '127.0.0.1' for local broker
        :param port: default '4333'
        :param listen_topics: dictfor example public.binance.order_book.*
        :param publish_topics: for example public.binance.order_book.BTC_USD
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        :param if_error: type of logs for errors
        :return: {'success': True} if success otherwise  {'success': False, 'error': 'error description'}
        """
        self.log = Logger(name='MessengerClient').log
        self.connected = False
        self.client_id = client_id
        self.host = host
        self.port = port
        self.queue = queue
        self.listen_topics_callbacks = listen_topics_callbacks
        self.publish_topics = publish_topics
        self.allow_reconnect = allow_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnecting_time_wait = reconnecting_time_wait
        self.if_error = if_error
        self.client_strategy = client_strategy
        self.pending_bytes_limit = pending_bytes_limit
        self._initialize_sub_class(client_strategy)
        #TODO: check that connect/sub/pub interface exist
        self._connect()


    def _initialize_sub_class(self, client_strategy):
        if client_strategy == 'asyncio':
            _AsyncioNATSClient.__init__()
        elif client_strategy == 'sync':
            _MultiProcNATSClient.__init__()


    def _connect_old(self):
        if self.client_strategy == 'asyncio':
            from messanger._msgr_client_v4 import _MessengerClient
            self.client = _MessengerClient().establish_connection(
                # client_id='client' + str(random.randint(1, 100)),
                client_id=self.client_id,
                broker_host=config.BROKER_HOST,
                port=config.PORT,
                listen_topics_callbacks=self.listen_topics_callbacks,
                publish_topics=self.publish_topics,
                queue=self.queue,
                allow_reconnect=config.ALLOW_RECONNECT,
                max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
                reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
            )
        elif self.client_strategy == 'in_current_process':
            from messanger._msgr_client_v2 import _MessengerClient
            self.client = _MessengerClient().establish_connection(
                # client_id='client' + str(random.randint(1, 100)),
                client_id=self.client_id,
                broker_host=config.BROKER_HOST,
                port=config.PORT,
                listen_topics_callbacks=self.listen_topics_callbacks,
                publish_topics=self.publish_topics,
                queue=self.queue,
                allow_reconnect=config.ALLOW_RECONNECT,
                max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
                reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
            )
        elif self.client_strategy == 'in_separate_processes':
            from messanger._msgr_client_v3 import _MessengerClient
            self.client = _MessengerClient().establish_connection(
                # client_id='client' + str(random.randint(1, 100)),
                client_id=self.client_id,
                broker_host=config.BROKER_HOST,
                port=config.PORT,
                listen_topics_callbacks=self.listen_topics_callbacks,
                publish_topics=self.publish_topics,
                queue=self.queue,
                allow_reconnect=config.ALLOW_RECONNECT,
                max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
                reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
            )

@singleton
class MessengerClient:

    def create_connection(self,
                          client_id: str,
                          broker_host: str,
                          port: int,
                          listen_topics_callbacks: dict,
                          allow_reconnect: bool or None,
                          max_reconnect_attempts: int or None,
                          reconnecting_time_wait: int or None,
                          if_error='warning', #warning or error
                          publish_topics=[],
                          # TODO: auth_credentialns
                          queue="",
                          client_strategy='in_current_process' # in_current_process' or in_separate_processes'
                          ):
        """
        :param client_id: instance identificator for NATS, str
        :param broker_ip: '127.0.0.1' for local broker
        :param port: default '4333'
        :param listen_topics: dictfor example public.binance.order_book.*
        :param publish_topics: for example public.binance.order_book.BTC_USD
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        :param if_error: type of logs for errors
        :return: {'success': True} if success otherwise  {'success': False, 'error': 'error description'}
        """
        if not hasattr(self, 'connected') or not self.connected:
            try:
                self.log = Logger(name='MessengerClient').log
                self.connected = False
                self.client_id = client_id
                self.broker_host = broker_host
                self.port = port
                self.queue = queue
                self.listen_topics_callbacks = listen_topics_callbacks
                self.publish_topics = publish_topics
                self.allow_reconnect = allow_reconnect
                self.max_reconnect_attempts = max_reconnect_attempts
                self.reconnecting_time_wait = reconnecting_time_wait
                self.if_error = if_error
                self.client_strategy = client_strategy
                self._launch()
                return {'success': True}
            except Exception as e:
                self.log(f'MessengerClient(interface) error: {str(e)}', level='error')
                return {'success': False, 'error': str(e)}
        else:
            self.log(f'Connection has already created', level='warning')
            return {'success': False, 'error': 'Connection has already created'}


    def _launch(self):
        if self.client_strategy == 'asyncio':
            from messanger._msgr_client_v4 import _MessengerClient
            self.client = _MessengerClient().establish_connection(
                # client_id='client' + str(random.randint(1, 100)),
                client_id=self.client_id,
                broker_host=config.BROKER_HOST,
                port=config.PORT,
                listen_topics_callbacks=self.listen_topics_callbacks,
                publish_topics=self.publish_topics,
                queue=self.queue,
                allow_reconnect=config.ALLOW_RECONNECT,
                max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
                reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
            )
        elif self.client_strategy == 'in_current_process':
            from messanger._msgr_client_v2 import _MessengerClient
            self.client = _MessengerClient().establish_connection(
                # client_id='client' + str(random.randint(1, 100)),
                client_id=self.client_id,
                broker_host=config.BROKER_HOST,
                port=config.PORT,
                listen_topics_callbacks=self.listen_topics_callbacks,
                publish_topics=self.publish_topics,
                queue=self.queue,
                allow_reconnect=config.ALLOW_RECONNECT,
                max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
                reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
            )
        elif self.client_strategy == 'in_separate_processes':
            from messanger._msgr_client_v3 import _MessengerClient
            self.client = _MessengerClient().establish_connection(
                # client_id='client' + str(random.randint(1, 100)),
                client_id=self.client_id,
                broker_host=config.BROKER_HOST,
                port=config.PORT,
                listen_topics_callbacks=self.listen_topics_callbacks,
                publish_topics=self.publish_topics,
                queue=self.queue,
                allow_reconnect=config.ALLOW_RECONNECT,
                max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
                reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
            )

    def check_connection(self):
        if self.client.check_connection:
            return True
        else:
            self.log(f'NATS connection status: {self.client.check_connection}', level='warning')

    def disconnect(self):
        self.client.disconnect()

    def publish(self, message, topic, reply_to=None):
        self.client.publish(message, topic, reply_to=reply_to)

    def publish_request(self, message, topic, timeout=10, unpack=True):
        return self.client.publish_request(message, topic, timeout=timeout, unpack=unpack)

    def publish_request_reply_to_another_topic(self, message, topic, reply_to=None):
       self.client.publish_request_reply_to_another_topic(message, topic, reply_to)

    async def aio_publish(self, message, topic, force=False):
        await self.client.aio_publish(message, topic, force=force)

    async def aio_publish_request(self, message, topic, timeout=10, unpack=True):
        return await self.client.aio_publish_request(message, topic, timeout, unpack=unpack)

    async def aio_publish_request_reply_to_another_topic(self, message, topic, reply_to=None):
       await self.client.aio_publish_request_reply_to_another_topic(message, topic, reply_to)






#for test
if __name__ == "__main__":

    def msg_generator():
        is_msgs_required = True
        time.sleep(5)
        while True:
            if is_msgs_required:
                n = 0
                for i in range(100):
                    msg = f'some message number {str(n)}'
                    cli.publish(msg, 'topic2.wqe')
                    n += 1
            time.sleep(2)


    def reciever_msg_handler(topic, msg):
        print(f"reciever_msg_handler <<<<< topic: {topic}, msg: {msg}")


    cli = MessengerClient()
    cli.create_connection(
        client_id='client'+str(random.randint(1,100)),
        broker_host=config.BROKER_HOST,
        port=config.PORT,
        listen_topics_callbacks={'topic2.wqe':reciever_msg_handler},
        # publish_topics=['topic2.wqe',],
        allow_reconnect=config.ALLOW_RECONNECT,
        max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
        reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
    )
    time.sleep(5)
    start_thread(msg_generator)
    import random

    while True:
        b = 1
        for i in range(100000000,10000000000):
            b = b + (i * random.randint(100000000,10000000000))
