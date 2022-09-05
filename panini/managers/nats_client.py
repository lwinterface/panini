import typing
import ujson
import asyncio
import threading
import nest_asyncio
from types import CoroutineType
from typing import Union, List
from nats.aio.client import Client as NATS
from nats.js import api
from panini.exceptions import DataTypeError, JetStreamNotEnabledError
from panini.managers.middleware_manager import MiddlewareManager
from panini.utils.logger import get_logger

NoneType = type(None)
nest_asyncio.apply()


class NATSClient:
    def __init__(
            self,
            host: Union[str, NoneType],
            port: Union[int, str],
            servers: Union[List[str], NoneType],
            client_nats_name: str,
            loop: asyncio.AbstractEventLoop,
            allow_reconnect: Union[bool, NoneType],
            max_reconnect_attempts: int = 60,
            reconnecting_time_wait: int = 2,
            auth: Union[dict, NoneType] = None,
            queue="",
            pending_bytes_limit=65536 * 1024 * 10,
            enable_js: bool = False,
            **kwargs
    ):
        """
        :param client_nats_name: instance identifier for NATS, str
        :param port: default '4222'
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        """
        if auth is None:
            auth = {}
        self.log = get_logger("panini")
        self.connected = False
        self.client_nats_name = client_nats_name
        self.host = host
        self.port = port
        self.servers = servers
        self.queue = queue
        self.auth = auth
        self.listen_subjects_callbacks = None
        self.allow_reconnect = allow_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnecting_time_wait = reconnecting_time_wait
        self.pending_bytes_limit = pending_bytes_limit
        self.enable_js = enable_js
        self.sub_map = {}

        self.include_subjects = None
        self.exclude_subjects = None

        self._middleware_manager = MiddlewareManager()

        def not_assigned_method(*args, **kwargs):
            raise Exception("used before assignment")

        self._publish_wrapped = not_assigned_method
        self._request_wrapped = not_assigned_method

        self._connection_kwargs = kwargs

        self.loop = loop

    def set_listen_subjects_callbacks(self, subscriptions: list):
        subscriptions = self.filter_subjects(subscriptions)
        self.listen_subjects_callbacks = subscriptions

    def start(self):
        # inject send_middlewares
        self._publish_wrapped = self._middleware_manager.wrap_function_by_middleware(
            "publish"
        )(self._publish)
        self._request_wrapped = self._middleware_manager.wrap_function_by_middleware(
            "request"
        )(self._request)

        self.loop.run_until_complete(self._establish_connection())

    @property
    def middleware_manager(self):
        return self._middleware_manager

    @property
    def middlewares(self):
        return self._middleware_manager.middlewares

    @middlewares.setter
    def middlewares(self, value: dict):
        self._middleware_manager.middlewares = value

    async def _panini_watcher(self):
        while True:
            await asyncio.sleep(1)
            if not self.client.is_connected and self.client.is_closed:
                exit(99)

    async def _establish_connection(self):
        self.client = NATS()
        if self.servers is None:
            server = 'nats://' + self.host + ":" + str(self.port)
            self.servers = [server]

        kwargs = {
            "servers": self.servers,
            "name": self.client_nats_name,
            **self._connection_kwargs
        }
        if self.allow_reconnect:
            kwargs["allow_reconnect"] = self.allow_reconnect
        if self.max_reconnect_attempts:
            kwargs["max_reconnect_attempts"] = self.max_reconnect_attempts
        if self.reconnecting_time_wait:
            kwargs["reconnect_time_wait"] = self.reconnecting_time_wait
        kwargs.update(self.auth)
        await self.client.connect(**kwargs)
        self.loop.create_task(self._panini_watcher())
        if self.enable_js:
            self.js_client = self.client.jetstream()
        if self.client.is_connected:
            listen_subjects_callbacks = self.listen_subjects_callbacks
            for subject, callbacks in listen_subjects_callbacks.items():
                for callback in callbacks:
                    await self.subscribe_new_subject(
                        subject, callback, init_subscription=True
                    )
            self.print_connect()

    def print_connect(self):
        print('\n======================================================================================')
        print(f'Panini service connected to NATS..')
        print(f"id: {self.client.client_id}")
        print(f"name: {self.client_nats_name}")
        print(f'\nNATS brokers:')
        for i in self.servers:
            print("* ",i)
        print('======================================================================================\n')

    def add_js_stream(self, name: str, subjects: List[str], config: api.StreamConfig = None, **params):
        if not self.enable_js:
            JetStreamNotEnabledError('Required flag "enable_js" is True')
        self.js_client.add_stream(name=name, subjects=subjects, config=config, **params)

    def subscribe_new_subject_sync(self, subject: str, callback: CoroutineType, **kwargs):
        self.loop.run_until_complete(self.subscribe_new_subject(subject, callback, **kwargs))

    async def subscribe_new_subject(
            self,
            subject: str,
            callback: CoroutineType,
            init_subscription=False,
            data_type=None,
            **kwargs
    ):
        if data_type == None:
            data_type = getattr(callback, 'data_type', 'json')

        callback = self._middleware_manager.wrap_function_by_middleware("listen")(callback)
        wrapped_callback = _ReceivedMessageHandler(self._publish, callback, data_type).call
        sub = await self.client.subscribe(
            subject,
            queue=self.queue,
            cb=wrapped_callback,
            pending_bytes_limit=self.pending_bytes_limit,
            **kwargs
        )

        if subject not in self.sub_map:
            self.sub_map[subject] = []
        self.sub_map[subject].append(sub)

        if init_subscription is False:
            if subject not in self.listen_subjects_callbacks:
                self.listen_subjects_callbacks[subject] = []
            self.listen_subjects_callbacks[subject].append(callback)
        return sub

    def unsubscribe_subject_sync(self, subject: str):
        self.loop.run_until_complete(self.unsubscribe_subject(subject))

    async def unsubscribe_subject(self, subject: str):
        if subject not in self.sub_map:
            raise Exception(f"Subject {subject} hasn't been subscribed")
        for sub in self.sub_map[subject]:
            await sub.unsubscribe()
        del self.sub_map[subject]
        del self.listen_subjects_callbacks[subject]

    def publish_sync(
            self,
            subject: str,
            message,
            reply_to: str = "",
            force: bool = False,
            data_type: type or str = "json",
            headers: dict = None,
    ):
        asyncio.ensure_future(
            self.publish(subject, message, reply_to, force, data_type, headers)
        )

    def publish_from_another_thread(self, subject: str, message):
        self.loop.call_soon_threadsafe(self.publish_sync, subject, message)

    def request_sync(
            self,
            subject: str,
            message,
            timeout: int = 10,
            data_type: type or str = "json",
            headers: dict = None,
    ):
        return self.loop.run_until_complete(
            self.request(subject, message, timeout, data_type, headers)
        )

    def request_from_another_thread_sync(
            self,
            subject: str,
            message,
            timeout: int = 10,
            headers: dict = None,
    ):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        return loop.run_until_complete(
            self.request_from_another_thread(subject, message, timeout, headers)
        )

    async def request_from_another_thread(
            self,
            subject: str,
            message,
            timeout: int = 10,
            headers: dict = None,
    ):
        fut = asyncio.run_coroutine_threadsafe(
            self.request(subject, message, timeout, headers=headers), self.loop
        )
        finished = threading.Event()

        def fut_finished_cb(_):
            finished.set()

        fut.add_done_callback(fut_finished_cb)
        await asyncio.get_event_loop().run_in_executor(None, finished.wait)
        return fut.result()

    @staticmethod
    def format_message_data_type(message, data_type):
        if type(message) in [dict, list] and data_type == "json":
            message = ujson.dumps(message)
            message = message.encode()
        elif type(message) is str and data_type is str:
            message = message.encode()
        elif type(message) is bytes and data_type is bytes:
            pass
        else:
            raise DataTypeError(
                f'Expected {"dict or list" if data_type in [dict, list, "json"] else data_type} but got {type(message)}'
            )

        return message

    async def _publish(
            self,
            subject: str,
            message,
            reply_to: str = '',
            force: bool = False,
            data_type: type or str = "json",
            headers: dict = None,
    ):
        message = self.format_message_data_type(message, data_type)
        await self.client.publish(subject=subject, payload=message, reply=reply_to, headers=headers)
        if force:
            await self.client.flush()
        await asyncio.sleep(0)

    async def publish(
            self,
            subject: str,
            message,
            reply_to: str = None,
            force: bool = False,
            data_type: type or str = "json",
            headers: dict = None,
    ):
        return await self._publish_wrapped(
            subject=subject,
            message=message,
            reply_to=reply_to,
            force=force,
            data_type=data_type,
            headers=headers
        )

    async def _request(
            self,
            subject: str,
            message,
            timeout: int = 10,
            data_type: type or str = "json",
            headers: dict = None,
    ):
        message = self.format_message_data_type(message, data_type)
        response = await self.client.request(subject, message, timeout=timeout, headers=headers)
        response = response.data
        if data_type == "json":
            response = ujson.loads(response)
        elif data_type is str:
            response = response.decode()
        return response

    async def request(
            self,
            subject: str,
            message,
            timeout: int = 10,
            data_type: type or str = "json",
            headers: dict = None,
    ):
        return await self._request_wrapped(
            subject=subject,
            message=message,
            timeout=timeout,
            data_type=data_type,
            headers=headers,
        )

    def disconnect_sync(self):
        self.loop.run_until_complete(self.disconnect())

    async def disconnect(self):
        await self.client.drain()
        self.log.warning("Disconnected")

    def check_connection(self):
        if self.client._status is NATS.CONNECTED:
            self.log.info("NATS Client status: CONNECTED")
            return True
        self.log.warning("NATS Client status: DISCONNECTED")

    def add_filters(self, include: list = None, exclude: list = None):
        self.include_subjects = include
        self.exclude_subjects = exclude

    def filter_subjects(self, subscriptions):
        assert not self.include_subjects or not self.exclude_subjects, "You can use either include or exclude. Not both"

        if self.include_subjects:
            for subject in subscriptions.copy():
                success = False
                for subject_include in self.include_subjects:
                    if subject_include in subject:
                        success = True
                        break
                if not success:
                    del subscriptions[subject]

        if self.exclude_subjects:
            for subject in subscriptions.copy():
                for subject_exclude in self.exclude_subjects:
                    if subject_exclude in subject:
                        del subscriptions[subject]
                        break

        return subscriptions


class _ReceivedMessageHandler:
    def __init__(self, publish_func, cb, data_type):
        self.publish_func = publish_func
        self.cb = cb
        self.data_type = data_type
        self.cb_is_async = asyncio.iscoroutinefunction(cb)

    async def call(self, msg):
        asyncio.ensure_future(self._call(msg))

    async def _call(self, msg):
        self.parse_data(msg)
        reply_to = self.match_msg_case(msg)
        if self.cb_is_async:
            response = await self.cb(msg)
        else:
            response = self.cb(msg)
        if reply_to is not None:
            await self.publish_func(reply_to, response)

    def parse_data(self, msg):
        if self.data_type == "raw" or self.data_type == bytes:
            return
        if self.data_type == str:
            msg.data = msg.data.decode()
        elif self.data_type == dict or self.data_type == "json":
            msg.data = ujson.loads(msg.data.decode())
        else:
            raise Exception(f"{self.data_type} is unsupported data format")

    def match_msg_case(self, msg):
        if not msg.reply == "":
            reply_to = msg.reply
        elif self.data_type == "json" and "reply_to" in msg.data:
            reply_to = msg.data.pop("reply_to")
        else:
            reply_to = None
        return reply_to
