from ..exceptions import InitializingNATSError
from .nats_client_interface import NATSClientInterface
from ._multi_proc_cli import _MultiProcNATSClient
from ._asyncio_cli import _AsyncioNATSClient
from ..managers import _MiddlewareManager


class NATSClient(NATSClientInterface):
    def __init__(
        self,
        client_id: str,
        host: str,
        port: int or str,
        listen_subjects_callbacks: dict,
        allow_reconnect: bool or None,
        max_reconnect_attempts: int = 60,
        reconnecting_time_wait: int = 2,
        publish_subjects=[],
        auth: dict = {},
        queue="",
        client_strategy="asyncio",
        redis_host="127.0.0.1",
        redis_port="6379",
        pending_bytes_limit=65536 * 1024 * 10,
        num_of_queues=1,
    ):
        """
        :param client_id: instance identifier for NATS, str
        :param port: default '4333'
        :param publish_subjects: for example public.binance.order_book.BTC_USD
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        :return: {'success': True} if success otherwise  {'success': False, 'error': 'error description'}
        """
        listen_subjects_callbacks = self.inject_listen_middlewares(
            listen_subjects_callbacks
        )
        if client_strategy == "sync":
            self.connector: NATSClientInterface = _MultiProcNATSClient(
                client_id,
                host,
                port,
                listen_subjects_callbacks,
                allow_reconnect,
                max_reconnect_attempts,
                reconnecting_time_wait,
                publish_subjects,
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
                listen_subjects_callbacks,
                allow_reconnect,
                max_reconnect_attempts,
                reconnecting_time_wait,
                publish_subjects,
                auth,
                queue,
                client_strategy,
                redis_host,
                redis_port,
                pending_bytes_limit,
                num_of_queues,
            )
            self.inject_send_middlewares()
        else:
            raise InitializingNATSError("Client strategy unsupported")

    def inject_listen_middlewares(self, listen_subjects_callbacks):
        injected = {}
        for s, callbacks in listen_subjects_callbacks.items():
            injected[s] = []
            for cb in callbacks:
                injected[s].append(
                    _MiddlewareManager._wrap_function_by_middleware(cb, "listen")
                )
        return injected

    def inject_send_middlewares(self):
        self.connector.publish = _MiddlewareManager._wrap_function_by_middleware(
            self.connector.publish, "publish"
        )
        self.connector.request = _MiddlewareManager._wrap_function_by_middleware(
            self.connector.request, "request"
        )

    def check_connection(self):
        self.connector.check_connection()

    def subscribe_new_subject(self, subject: str, callback):
        callback = _MiddlewareManager._wrap_function_by_middleware(callback, "listen")
        self.connector.subscribe_new_subject(subject, callback)

    async def aio_subscribe_new_subject(self, subject: str, callback):
        callback = _MiddlewareManager._wrap_function_by_middleware(callback, "listen")
        return await self.connector.aio_subscribe_new_subject(subject, callback)

    async def aio_unsubscribe_subject(self, subject: str):
        await self.connector.aio_unsubscribe_subject(subject)

    def unsubscribe_ssid(self, ssid: int):
        self.connector.unsubscribe_ssid(ssid)

    async def aio_unsubscribe_ssid(self, ssid: int):
        await self.connector.aio_unsubscribe_ssid(ssid)

    def disconnect(self):
        self.connector.disconnect()

    def publish_sync(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        self.connector.publish_sync(
            subject, message, reply_to=reply_to, force=force, data_type=data_type
        )

    def request_sync(
        self,
        subject: str,
        message,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
    ):
        return self.connector.request_sync(
            subject, message, timeout=timeout, data_type=data_type
        )

    async def publish(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        await self.connector.publish(
            subject, message, reply_to=reply_to, force=force, data_type=data_type
        )

    async def request(
        self,
        subject: str,
        message,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
    ):
        return await self.connector.request(
            subject, message, timeout=timeout, data_type=data_type
        )

    def request_from_another_thread_sync(
        self, subject: str, message, timeout: int = 10
    ):
        return self.connector.request_from_another_thread_sync(
            subject, message, timeout
        )

    async def request_from_another_thread(
        self, subject: str, message, timeout: int = 10
    ):
        return await self.connector.request_from_another_thread(
            subject, message, timeout
        )
