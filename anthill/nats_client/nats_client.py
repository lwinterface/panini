import time
import random
from ..utils.helper import start_thread
from ._asyncio_cli import _AsyncioNATSClient
from ._multi_proc_cli import _MultiProcNATSClient
from ..exceptions import InitializingNATSError
from ..utils.logger import get_logger

message = None


class NATSClient:

    def __init__(self,
            client_id: str,
            host: str,
            port: int or str,
            listen_topics_callbacks: dict,
            allow_reconnect: bool or None,
            max_reconnect_attempts: int = 60,
            reconnecting_time_wait: int = 2,
            publish_topics=[],
            auth: dict={},
            queue="",
            client_strategy='asyncio',  # in_current_process' or in_separate_processes'
            redis_host='127.0.0.1',
            redis_port='6379',
            pending_bytes_limit=65536 * 1024 * 10,
            num_of_queues=1,
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
        :return: {'success': True} if success otherwise  {'success': False, 'error': 'error description'}
        """
        self.log = get_logger('anthill')
        self.connected = False
        self.client_id = client_id
        self.host = host
        self.port = port
        self.queue = queue
        self.auth = auth
        self.listen_topics_callbacks = listen_topics_callbacks
        self.publish_topics = publish_topics
        self.allow_reconnect = allow_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnecting_time_wait = reconnecting_time_wait
        self.client_strategy = client_strategy
        self.pending_bytes_limit = pending_bytes_limit
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.num_of_queues = num_of_queues
        self._initialize_sub_class(client_strategy)
        # TODO: check that connect/sub/pub interface exist
        global message
        message = self

    def _initialize_sub_class(self, client_strategy: str):
        if client_strategy == 'asyncio':
            self.connector = _AsyncioNATSClient(self)
        elif client_strategy == 'sync':
            self.connector = _MultiProcNATSClient(self)
        else:
            raise InitializingNATSError('Client strategy unsupported')

    def check_connection(self):
        if self.connector.client.check_connection:
            return True
        else:
            self.log.warning(f'NATS connection status: {self.connector.client.check_connection}')

    def subscribe_new_topic(self, topic: str, callback):
        self.connector.subscribe_new_topic(topic, callback)

    def disconnect(self):
        self.connector.client.disconnect()

    def publish(self, message, topic: str):
        self.connector.publish(message, topic)

    def publish_request(self, message, topic: str, timeout: int = 10, unpack: bool = True):
        return self.connector.publish_request(message, topic, timeout=timeout, unpack=unpack)

    def publish_request_with_reply_to_another_topic(self, message, topic: str, reply_to: str = None):
        self.connector.publish_request_with_reply_to_another_topic(message, topic, reply_to)

    async def aio_publish(self, message, topic: str, force: bool = False):
        await self.connector.aio_publish(message, topic, force=force)

    async def aio_publish_request(self, message, topic: str, timeout: int = 10, unpack: bool = True):
        return await self.connector.aio_publish_request(message, topic, timeout, unpack=unpack)

    async def aio_publish_request_with_reply_to_another_topic(self, message, topic: str, reply_to: str = None):
        await self.connector.aio_publish_request_with_reply_to_another_topic(message, topic, reply_to)


# for test
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


    cli = NATSClient(
        client_id='client' + str(random.randint(1, 100)),
        host='127.0.0.1',
        port='4222',
        listen_topics_callbacks={'topic2.wqe': reciever_msg_handler},
        # publish_topics=['topic2.wqe',],
        allow_reconnect=True,
        max_reconnect_attempts=10,
        reconnecting_time_wait=1,
    )
    time.sleep(5)
    start_thread(msg_generator)
    import random

    while True:
        b = 1
        for i in range(100000000, 10000000000):
            b = b + (i * random.randint(100000000, 10000000000))
