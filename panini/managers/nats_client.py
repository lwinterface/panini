import asyncio
import threading
import nest_asyncio
from typing import Union, List, Dict
from nats.aio.client import Client as NATS
from panini.exceptions import JetStreamNotEnabledError, UnsubscribeError, InitializingNATSError, MessageSchemaError
from panini.managers.event_manager import JsListen, Listen
from panini.managers.middleware_manager import MiddlewareManager
from panini.managers.schema_manager import SchemaManager
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
        self.logger = get_logger("panini")
        self.connected = False
        self.client_nats_name = client_nats_name
        self.host = host
        self.port = port
        self.servers = servers
        self.queue = queue
        self.auth = auth
        self.listeners = None
        self.js_listeners = None
        self.allow_reconnect = allow_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnecting_time_wait = reconnecting_time_wait
        self.pending_bytes_limit = pending_bytes_limit
        self.enable_js = enable_js
        self.sub_map = {}
        self.js_stream_map = {}

        self.include_subjects = None
        self.exclude_subjects = None

        self._middleware_manager = MiddlewareManager()

        def not_assigned_method(*args, **kwargs):
            raise InitializingNATSError("used before assignment")

        self._publish_wrapped = not_assigned_method
        self._request_wrapped = not_assigned_method

        self._connection_kwargs = kwargs

        self.loop = loop

    @property
    def js(self):
        if not hasattr(self, "_js"):
            raise JetStreamNotEnabledError("JetStream is not enabled! Use enable_js=True when create Panini app.")
        return self._js

    def set_listeners(self, subscriptions: Dict, js_subscriptions: Dict):
        subscriptions = self.filter_subjects(subscriptions)
        self.listeners = subscriptions
        self.js_listeners = js_subscriptions


    def start(self):
        # inject send_middlewares
        self._publish_wrapped = self._middleware_manager.wrap_function_by_middleware(
            "publish"
        )(self._publish)
        self._publish_js_wrapped = self._middleware_manager.wrap_function_by_middleware(
            "publish"
        )(self._publish_js)
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
            self._js = self.client.jetstream()

    async def subscribe_listeners(self):
        if not self.client.is_connected:
            raise InitializingNATSError("NATS Client hasn't connected")
        for subject, listeners_single_subject in self.listeners.items():
            for listener in listeners_single_subject:
                await self.subscribe_new_subject(listener)
        self.loop.create_task(self.listen_js_subscriptions())

    async def listen_js_subscriptions(self):
        for subject, js_listeners_single_subject in self.js_listeners.items():
            for js_listener in js_listeners_single_subject:
                await self.subscribe_new_js(js_listener)

    def print_connect(self):
        if not self.client.is_connected:
            raise InitializingNATSError("NATS Client hasn't connected")
        print("\n======================================================================================")
        print(f"Panini service connected to NATS..")
        print(f"id: {self.client.client_id}")
        print(f"name: {self.client_nats_name}")
        print(f"\nNATS brokers:")
        for i in self.servers:
            print("* ", i)
        print(f"\nJetStream enabled: {self.enable_js}")
        print("======================================================================================\n")

    def subscribe_new_subject_sync(self, listener: Listen):
        self.loop.run_until_complete(self.subscribe_new_subject(listener))

    async def subscribe_new_subject(self, listener: Listen):
        params = listener.__dict__
        subject = params.pop("subject")
        callback = params.pop("callback")
        data_type = params.pop("data_type")
        queue = params.pop("queue")
        if not queue:
            queue = self.queue

        callback_with_middleware = self._middleware_manager.wrap_function_by_middleware("listen")(callback)
        wrapped_callback = _ReceivedMessageHandler(self._publish, callback_with_middleware, data_type).call
        sub = await self.client.subscribe(
            subject,
            cb=wrapped_callback,
            pending_bytes_limit=self.pending_bytes_limit,
            queue=queue,
        )

        if subject not in self.sub_map:
            self.sub_map[subject] = []
        self.sub_map[subject].append(sub)
        return sub

    async def subscribe_new_js(self, js_listener: JsListen):
        params = js_listener.__dict__
        callback = params.pop("callback")
        data_type = params.pop("data_type")
        queue = params.pop("queue")
        if not queue:
            queue = self.queue
        callback_with_middleware = self._middleware_manager.wrap_function_by_middleware("listen")(callback)
        wrapped_callback = _ReceivedMessageHandler(self._publish, callback_with_middleware, data_type).call_js

        sub = await self.js.subscribe(
            queue=queue,
            cb=wrapped_callback,
            **params
        )
        stream = sub._stream
        if stream not in self.js_stream_map:
            self.js_stream_map[stream] = []
        self.js_stream_map[stream].append(sub)
        return sub

    def unsubscribe_subject_sync(self, subject: str):
        self.loop.run_until_complete(self.unsubscribe_subject(subject))

    async def unsubscribe_subject(self, subject: str):
        if subject not in self.sub_map:
            raise UnsubscribeError(f"Subject {subject} hasn't been subscribed")
        for sub in self.sub_map[subject]:
            await sub.unsubscribe()
        del self.sub_map[subject]

    async def unsubscribe_js_listen(self, stream: str):
        if stream not in self.js_stream_map:
            raise UnsubscribeError(f"Stream {stream} hasn't been subscribed")
        for js_listener in self.js_stream_map[stream]:
            await js_listener.unsubscribe()
        del self.js_stream_map[stream]
        del self.js_listeners[stream]

    def publish_sync(
            self,
            subject: str,
            message,
            reply_to: str = "",
            force: bool = False,
            headers: dict = None,
    ):
        asyncio.ensure_future(
            self.publish(subject, message, reply_to, force, headers)
        )

    def publish_from_another_thread(self, subject: str, message):
        self.loop.call_soon_threadsafe(self.publish_sync, subject, message)

    def request_sync(
            self,
            subject: str,
            message,
            timeout: int = 10,
            response_data_type: type = dict,
            headers: dict = None,
    ):
        return self.loop.run_until_complete(
            self.request(subject, message, timeout, response_data_type, headers)
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
        return SchemaManager.deserialize_message(
            data_type=data_type,
            message=message
        )

    async def _publish(
            self,
            subject: str,
            message,
            reply_to: str = '',
            force: bool = False,
            headers: dict = None,
    ):
        message = self.format_message_data_type(message, type(message))
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
            headers: dict = None,
    ):
        return await self._publish_wrapped(
            subject=subject,
            message=message,
            reply_to=reply_to,
            force=force,
            headers=headers
        )

    async def _request(
            self,
            subject: str,
            message,
            timeout: int = 10,
            response_data_type: type = dict,
            headers: dict = None,
    ):
        message = self.format_message_data_type(message, type(message))
        response = await self.client.request(subject, message, timeout=timeout, headers=headers)
        return SchemaManager.serialize_message(response_data_type, response.data)

    async def request(
            self,
            subject: str,
            message,
            timeout: int = 10,
            response_data_type: type = dict,
            headers: dict = None,
    ):
        return await self._request_wrapped(
            subject=subject,
            message=message,
            timeout=timeout,
            response_data_type=response_data_type,
            headers=headers,
        )

    async def _publish_js(
            self,
            subject: str,
            message,
            timeout: float = None,
            stream: str = None,
            headers: dict = None
    ) :
        payload: bytes = self.format_message_data_type(message, type(message))
        return await self._js.publish(
                subject=subject,
                payload=payload,
                timeout=timeout,
                stream=stream,
                headers=headers
        )

    async def publish_js(
            self,
            subject: str,
            message,
            timeout: float = None,
            stream: str = None,
            headers: dict = None,
    ):
        return await self._publish_js(
            subject=subject,
            message=message,
            timeout=timeout,
            stream=stream,
            headers=headers,
        )

    async def _publish_js(
            self,
            subject: str,
            message,
            timeout: float = None,
            stream: str = None,
            data_type: type = dict,
            headers: dict = None
    ) :
        payload: bytes = self.format_message_data_type(message, data_type)
        return await self._js.publish(
                subject=subject,
                payload=payload,
                timeout=timeout,
                stream=stream,
                headers=headers
        )

    async def publish_js(
            self,
            subject: str,
            message,
            timeout: float = None,
            stream: str = None,
            data_type: type = dict,
            headers: dict = None,
    ):
        return await self._publish_js(
            subject=subject,
            message=message,
            timeout=timeout,
            stream=stream,
            data_type=data_type,
            headers=headers,
        )

    def disconnect_sync(self):
        self.loop.run_until_complete(self.disconnect())

    async def disconnect(self):
        await self.client.drain()
        self.logger.warning("Disconnected")

    def check_connection(self):
        if self.client._status is NATS.CONNECTED:
            self.logger.info("NATS Client status: CONNECTED")
            return True
        self.logger.warning("NATS Client status: DISCONNECTED")

    def add_filters(self, include: list = None, exclude: list = None):
        self.include_subjects = include
        self.exclude_subjects = exclude

    def filter_subjects(self, subscriptions):
        assert not self.include_subjects or not self.exclude_subjects, "You can use either include or exclude. Not both"
        if self.include_subjects:
            return self._filter_include(subscriptions)
        elif self.exclude_subjects:
            return self._filter_exclude(subscriptions)
        else:
            return subscriptions

    def _filter_include(self, subscriptions: Dict):
        def subject_included(subject):
            for subject_included in self.include_subjects:
                if subject_included not in subject:
                    continue
                return True
        return {
            subject: listeners
            for subject, listeners in subscriptions.items()
            if subject_included(subject)
        }

    def _filter_exclude(self, subscriptions: Dict):
        def subject_excluded(subject):
            for subject_excluded in self.exclude_subjects:
                if subject_excluded in subject:
                    return False
            return True
        return {
            subject: listeners
            for subject, listeners in subscriptions.items()
            if subject_excluded(subject)
        }

class _ReceivedMessageHandler:
    def __init__(self, publish_func, cb, data_type):
        self.publish_func = publish_func
        self.cb = cb
        self.data_type = data_type
        self.cb_is_async = asyncio.iscoroutinefunction(cb)
        self.logger = get_logger("panini")

    async def call(self, msg):
        asyncio.ensure_future(self._call(msg))

    async def call_js(self, msg):
        asyncio.ensure_future(self._call_js(msg))

    async def _call(self, msg):
        reply_to, response = await self._call_main(msg)
        if reply_to is not None:
            await self.publish_func(reply_to, response)

    async def _call_js(self, msg):
        reply_to, response = await self._call_main(msg)
        if reply_to is not None:
            if reply_to.startswith("$JS."):
                return
            await self.publish_func(reply_to, response)

    async def _call_main(self, msg):
        reply_to = self.match_msg_case(msg)
        msg_error = self.parse_data(msg)
        if msg_error:
            return reply_to, msg_error
        if self.cb_is_async:
            response = await self.cb(msg)
        else:
            response = self.cb(msg)
        return reply_to, response

    def parse_data(self, msg):
        try:
            msg.data = SchemaManager.serialize_message(
                data_type=self.data_type,
                message=msg.data
            )
        except MessageSchemaError as mse:
            self.logger.error(mse)
            return {"success": False, "error": "MessageSchemaError"}

    def match_msg_case(self, msg):
        if msg.reply != "":
            reply_to = msg.reply
        else:
            reply_to = None
        return reply_to
