import typing
import ujson
import asyncio
import threading
import nest_asyncio
from types import CoroutineType
from nats.aio.client import Client as NATS
from panini.exceptions import DataTypeError
from panini.utils.logger import get_logger
from panini.managers import _MiddlewareManager

nest_asyncio.apply()


class Msg:
    """
    Alternative implementation of the class with "context" field
    """

    __slots__ = ("subject", "reply", "data", "sid", "context")

    def __init__(self, subject="", reply="", data=b"", sid=0, context=None):
        if context is None:
            context = {}
        self.subject = subject
        self.reply = reply
        self.data = data
        self.sid = sid
        self.context = context

    def __repr__(self):
        return "<{}: subject='{}' reply='{}' context='{}...'>".format(
            self.__class__.__name__,
            self.subject,
            self.reply,
            self.context,
        )


class NATSClient:
    def __init__(
        self,
        client_id: str,
        host: str,
        port: int or str,
        listen_subjects_callbacks: dict,
        allow_reconnect: bool or None,
        max_reconnect_attempts: int = 60,
        reconnecting_time_wait: int = 2,
        auth: dict = None,
        queue="",
        pending_bytes_limit=65536 * 1024 * 10,
    ):
        """
        :param client_id: instance identifier for NATS, str
        :param port: default '4222'
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        """
        if auth is None:
            auth = {}
        self.log = get_logger("panini")
        self.connected = False
        self.client_id = client_id
        self.host = host
        self.port = port
        self.queue = queue
        self.auth = auth
        self.listen_subjects_callbacks = listen_subjects_callbacks
        self.allow_reconnect = allow_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnecting_time_wait = reconnecting_time_wait
        self.pending_bytes_limit = pending_bytes_limit
        self.ssid_map = {}

        # inject send_middlewares
        self._publish_wrapped = _MiddlewareManager._wrap_function_by_middleware(
            "publish"
        )(self._publish)
        self._request_wrapped = _MiddlewareManager._wrap_function_by_middleware(
            "request"
        )(self._request)

        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self._establish_connection())

    async def _establish_connection(self):
        # TODO: authorization
        self.client = NATS()
        self.client.msg_class = Msg
        self.server = self.host + ":" + str(self.port)
        kwargs = {"servers": self.server, "loop": self.loop, "name": self.client_id}
        if self.allow_reconnect:
            kwargs["allow_reconnect"] = self.allow_reconnect
        if self.max_reconnect_attempts:
            kwargs["max_reconnect_attempts"] = self.max_reconnect_attempts
        if self.reconnecting_time_wait:
            kwargs["reconnect_time_wait"] = self.reconnecting_time_wait
        kwargs.update(self.auth)
        await self.client.connect(**kwargs)
        if self.client.is_connected:
            listen_subjects_callbacks = self.listen_subjects_callbacks
            for subject, callbacks in listen_subjects_callbacks.items():
                for callback in callbacks:
                    await self.subscribe_new_subject(
                            subject, callback, init_subscription=True
                        )

    def subscribe_new_subject_sync(self, subject: str, callback: CoroutineType, **kwargs):
        self.loop.run_until_complete(self.subscribe_new_subject(subject, callback, **kwargs))

    async def subscribe_new_subject(
        self,
        subject: str,
        callback: CoroutineType,
        init_subscription=False,
        is_async=False,
        data_type=None
    ):
        if data_type == None:
            data_type = getattr(callback, 'data_type', 'json.loads')
        callback = _MiddlewareManager._wrap_function_by_middleware("listen")(callback)
        wrapped_callback = _ReceivedMessageHandler(self._publish, callback, data_type)
        ssid = await self.client.subscribe(
            subject,
            queue=self.queue,
            cb=wrapped_callback,
            pending_bytes_limit=self.pending_bytes_limit,
            is_async=is_async,
        )
        if subject not in self.ssid_map:
            self.ssid_map[subject] = []
        self.ssid_map[subject].append(ssid)
        if init_subscription is False:
            if subject not in self.listen_subjects_callbacks:
                self.listen_subjects_callbacks[subject] = []
            self.listen_subjects_callbacks[subject].append(callback)
        return ssid

    def unsubscribe_subject_sync(self, subject: str):
        self.loop.run_until_complete(self.unsubscribe_subject(subject))

    async def unsubscribe_subject(self, subject: str):
        if subject not in self.ssid_map:
            raise Exception(f"Subject {subject} hasn't been subscribed")
        for ssid in self.ssid_map[subject]:
            await self.client.unsubscribe(ssid)
        del self.ssid_map[subject]
        del self.listen_subjects_callbacks[subject]

    def unsubscribe_ssid_sync(self, ssid: int, subject: str = None):
        self.loop.run_until_complete(self.unsubscribe_ssid(ssid, subject))

    async def unsubscribe_ssid(self, ssid: int, subject: str = None):
        if subject and subject not in self.ssid_map:
            raise Exception(f"Subject {subject} hasn't been subscribed")
        await self.client.unsubscribe(ssid)
        if subject:
            del self.ssid_map[subject]
            del self.listen_subjects_callbacks[subject]
        else:
            for subject in self.ssid_map:
                if ssid in self.ssid_map[subject]:
                    self.ssid_map[subject].remove(ssid)
            for subject in self.listen_subjects_callbacks:
                if ssid in self.listen_subjects_callbacks[subject]:
                    self.listen_subjects_callbacks[subject].remove(ssid)

    def publish_sync(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        asyncio.ensure_future(
            self.publish(subject, message, reply_to, force, data_type)
        )

    def publish_from_another_thread(self, subject: str, message):
        self.loop.call_soon_threadsafe(self.publish_sync, subject, message)

    def request_sync(
        self,
        subject: str,
        message,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
        callback: typing.Callable = None,
    ):
        # asyncio.ensure_future(self.request(subject, message, timeout, data_type))
        return self.loop.run_until_complete(
            self.request(subject, message, timeout, data_type, callback)
        )

    def request_from_another_thread_sync(
        self,
        subject: str,
        message,
        timeout: int = 10,
    ):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        return loop.run_until_complete(
            self.request_from_another_thread(subject, message, timeout)
        )

    async def request_from_another_thread(
        self,
        subject: str,
        message,
        timeout: int = 10,
    ):
        # return self.loop.call_soon_threadsafe(self.request_sync, subject, message, timeout)
        fut = asyncio.run_coroutine_threadsafe(
            self.request(subject, message, timeout), self.loop
        )
        finished = threading.Event()

        def fut_finished_cb(_):
            finished.set()

        fut.add_done_callback(fut_finished_cb)
        await asyncio.get_event_loop().run_in_executor(None, finished.wait)
        return fut.result()

    @staticmethod
    def format_message_data_type(message, data_type):
        if type(message) in [dict, list] and data_type == "json.dumps":
            message = ujson.dumps(message)
            message = message.encode()
        elif type(message) is str and data_type is str:
            message = message.encode()
        elif type(message) is bytes and data_type is bytes:
            pass
        else:
            raise DataTypeError(
                f'Expected {"dict" if data_type in [dict, "json.dumps"] else data_type} but got {type(message)}'
            )

        return message

    async def _publish(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        message = self.format_message_data_type(message, data_type)

        if reply_to is not None:
            await self.client.publish_request(subject, reply_to, message)
        else:
            await self.client.publish(subject, message)
        if force:
            await self.client.flush()

    async def publish(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        return await self._publish_wrapped(
            subject=subject,
            message=message,
            reply_to=reply_to,
            force=force,
            data_type=data_type,
        )

    async def _request(
        self,
        subject: str,
        message,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
        callback: typing.Callable = None,
    ):
        message = self.format_message_data_type(message, data_type)
        if callback is not None:
            return await self.client.request(subject, message, cb=callback)
        response = await self.client.request(subject, message, timeout=timeout)
        response = response.data
        if data_type == "json.dumps":
            response = ujson.loads(response)
        elif data_type is str:
            response = response.decode()
        return response

    async def request(
        self,
        subject: str,
        message,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
        callback: typing.Callable = None,
    ):
        return await self._request_wrapped(
            subject=subject,
            message=message,
            timeout=timeout,
            data_type=data_type,
            callback=callback,
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


class _ReceivedMessageHandler:
    def __init__(self, publish_func, cb, data_type):
        self.publish_func = publish_func
        self.cb = cb
        self.data_type = data_type
        self.cb_is_async = asyncio.iscoroutinefunction(cb)

    def __call__(self, msg):
        asyncio.ensure_future(self.call(msg))

    async def call(self, msg):
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
        elif self.data_type == dict or self.data_type == "json.loads":
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
