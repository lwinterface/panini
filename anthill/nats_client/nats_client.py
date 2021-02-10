import time
import random
from ..utils.helper import start_thread
from abc import ABC, abstractmethod

from ..exceptions import InitializingNATSError
from ..utils.logger import get_logger
from ._nats_client_interface import NATSClientInterface
from ._multi_proc_cli import _MultiProcNATSClient
from ._asyncio_cli import _AsyncioNATSClient


class NATSClient(NATSClientInterface):
    def __init__(
        self,
        client_id: str,
        host: str,
        port: int or str,
        listen_topics_callbacks: dict,
        allow_reconnect: bool or None,
        max_reconnect_attempts: int = 60,
        reconnecting_time_wait: int = 2,
        publish_topics=[],
        auth: dict = {},
        queue="",
        client_strategy="asyncio",
        redis_host="127.0.0.1",
        redis_port="6379",
        pending_bytes_limit=65536 * 1024 * 10,
        num_of_queues=1,
    ):
        """
        :param client_id: instance identificator for NATS, str
        :param port: default '4333'
        :param publish_topics: for example public.binance.order_book.BTC_USD
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        :return: {'success': True} if success otherwise  {'success': False, 'error': 'error description'}
        """

        if client_strategy == "sync":
            self.connector: NATSClientInterface = _MultiProcNATSClient(
                client_id,
                host,
                port,
                listen_topics_callbacks,
                allow_reconnect,
                max_reconnect_attempts,
                reconnecting_time_wait,
                publish_topics,
                auth,
                queue,
                client_strategy,
                redis_host,
                redis_port,
                pending_bytes_limit,
                num_of_queues,
            )
        elif client_strategy == "asyncio":
            self.connector: NATSClientInterface = _AsyncioNATSClient(
                client_id,
                host,
                port,
                listen_topics_callbacks,
                allow_reconnect,
                max_reconnect_attempts,
                reconnecting_time_wait,
                publish_topics,
                auth,
                queue,
                client_strategy,
                redis_host,
                redis_port,
                pending_bytes_limit,
                num_of_queues,
            )
        else:
            raise InitializingNATSError("Client strategy unsupported")

    def check_connection(self):
        self.connector.check_connection()

    def subscribe_new_topic(self, topic: str, callback):
        self.connector.subscribe_new_topic(topic, callback)

    def disconnect(self):
        self.connector.disconnect()

    def publish_sync(self, topic: str, message: dict, reply_to: str = None):
        self.connector.publish_sync(topic, message, reply_to)

    def request_sync(
        self, topic: str, message: dict, timeout: int = 10, unpack: bool = True
    ):
        return self.connector.request_sync(topic, message, timeout, unpack)

    async def publish(
        self, topic: str, message: dict, reply_to: str = None, force: bool = False
    ):
        await self.connector.publish(topic, message, reply_to, force)

    async def request(
        self, topic: str, message: dict, timeout: int = 10, unpack: bool = True
    ):
        return await self.connector.request(topic, message, timeout, unpack)
