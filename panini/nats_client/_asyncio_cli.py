import json
import asyncio
import uuid
import threading
import nest_asyncio
from types import CoroutineType
from nats.aio.client import Client as NATS
from ..utils.helper import is_json, run_coro_threadsafe, validate_msg, register_msg
from ..exceptions import DataTypeError
from ..utils.logger import get_logger
from ._nats_client_interface import NATSClientInterface

nest_asyncio.apply()

log = get_logger("panini")
isr_log = get_logger("inter_services_request")


class Msg:
    """
    Alternative implementation of the class with "context" field
    """

    __slots__ = ("subject", "reply", "data", "sid", "context")

    def __init__(self, subject="", reply="", data=b"", sid=0, context={}):
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


class _AsyncioNATSClient(NATSClientInterface):
    """
    Sub interface for NATSClient, create asyncio NATS connection for sending and listening
    """

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
        client_strategy="asyncio",  # in_current_process' or in_separate_processes'
        redis_host="127.0.0.1",
        redis_port="6379",
        pending_bytes_limit=65536 * 1024 * 10,
        num_of_queues=1,
    ):
        super().__init__(
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
        self.ssid_map = {}
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
                    await self.aio_subscribe_new_subject(
                        subject, callback, init_subscribtion=True
                    )

    def subscribe_new_subject(self, subject: str, callback: CoroutineType):
        self.loop.run_until_complete(self.aio_subscribe_new_subject(subject, callback))

    async def aio_subscribe_new_subject(
        self, subject: str, callback: CoroutineType, init_subscribtion=False
    ):
        wrapped_callback = _RecievedMessageHandler(self.publish, callback)
        ssid = await self.client.subscribe(
            subject,
            queue=self.queue,
            cb=wrapped_callback,
            pending_bytes_limit=self.pending_bytes_limit,
        )
        if not subject in self.ssid_map:
            self.ssid_map[subject] = []
        self.ssid_map[subject].append(ssid)
        if init_subscribtion is False:
            if not subject in self.listen_subjects_callbacks:
                self.listen_subjects_callbacks[subject] = []
            self.listen_subjects_callbacks[subject].append(callback)
        return ssid

    def unsubscribe_subject(self, topic: str):
        self.loop.run_until_complete(self.aio_unsubscribe_subject(topic))

    async def aio_unsubscribe_subject(self, subject: str):
        if not subject in self.ssid_map:
            raise Exception(f"Subject {subject} hasn't been subscribed")
        for ssid in self.ssid_map[subject]:
            await self.client.unsubscribe(ssid)
        del self.ssid_map[subject]
        del self.listen_subjects_callbacks[subject]

    async def aio_unsubscribe_ssid(self, ssid: int, topic: str = None):
        if topic and not topic in self.ssid_map:
            raise Exception(f"Subject {topic} hasn't been subscribed")
        await self.client.unsubscribe(ssid)
        if topic:
            del self.ssid_map[topic]
            del self.listen_subjects_callbacks[topic]
        else:
            for topic in self.ssid_map:
                if ssid in self.ssid_map[topic]:
                    self.ssid_map[topic].remove(ssid)
            for topic in self.listen_subjects_callbacks:
                if ssid in self.listen_subjects_callbacks[topic]:
                    self.listen_subjects_callbacks[topic].remove(ssid)

    def publish_sync(
        self,
        subject: str,
        message: dict,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        if reply_to is not None:
            return self._publish_request_with_reply_to_another_subject(
                subject, message, reply_to, force, data_type
            )

        asyncio.ensure_future(
            self.publish(subject, message, reply_to, force, data_type)
        )

    def _publish_request_with_reply_to_another_subject(
        self,
        subject: str,
        message: dict,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        asyncio.ensure_future(
            self.aio_publish_request_with_reply_to_another_subject(
                subject, message, reply_to, force, data_type
            )
        )

    def publish_from_another_thread(self, subject: str, message: dict):
        self.loop.call_soon_threadsafe(self.publish_sync, subject, message)

    def request_sync(
        self,
        subject: str,
        message: dict,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
    ):
        # asyncio.ensure_future(self.request(subject, message, timeout, data_type))
        return self.loop.run_until_complete(
            self.request(subject, message, timeout, data_type)
        )

    def request_from_another_thread(
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
            self.aio_request_from_another_thread(subject, message, timeout)
        )

    async def aio_request_from_another_thread(
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

    async def publish(
        self,
        subject: str,
        message: dict,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        if reply_to is not None:
            return await self.aio_publish_request_with_reply_to_another_subject(
                subject, message, reply_to, force, data_type
            )

        if type(message) is dict and data_type == "json.dumps":
            message = json.dumps(message)
            message = message.encode()
        elif type(message) is str and data_type is str:
            message = message.encode()
        elif type(message) is bytes and data_type is bytes:
            pass
        else:
            raise DataTypeError(
                f'Expected {"dict" if data_type in [dict, "json.dumps"] else data_type} but got {type(message)}'
            )
        await self.client.publish(subject, message)
        if force:
            await self.client.flush()

    async def request(
        self,
        subject: str,
        message: dict,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
    ):
        if type(message) is dict and data_type == "json.dumps":
            message = json.dumps(message)
            message = message.encode()
        elif type(message) is str and data_type is str:
            message = message.encode()
        elif type(message) is bytes and data_type is bytes:
            pass
        else:
            raise DataTypeError(
                f'Expected {"dict" if data_type in [dict, "json.dumps"] else data_type} but got {type(message)}'
            )
        response = await self.client.request(subject, message, timeout=timeout)
        response = response.data
        if data_type == "json.dumps":
            response = json.loads(response)
        elif data_type is str:
            response = response.decode()
        return response

    async def aio_publish_request_with_reply_to_another_subject(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        if type(message) is dict and data_type == "json.dumps":
            message = json.dumps(message)
            message = message.encode()
        elif type(message) is str and data_type is str:
            message = message.encode()
        elif type(message) is bytes and data_type is bytes:
            pass
        else:
            raise DataTypeError(
                f'Expected {"dict" if data_type in [dict, "json.dumps"] else data_type} but got {type(message)}'
            )
        await self.client.publish_request(subject, reply_to, message)
        if force:
            await self.client.flush()

    def disconnect(self):
        self.loop.run_until_complete(self.aio_disconnect())
        log.warning("Disconnected")

    async def aio_disconnect(self):
        await self.client.drain()
        log.warning("Disconnected")

    def check_connection(self):
        if self.client._status is NATS.CONNECTED:
            log.info("NATS Client status: CONNECTED")
            return True
        log.warning("NATS Client status: DISCONNECTED")


class _RecievedMessageHandler:
    def __init__(self, publish_func, cb):
        self.publish_func = publish_func
        self.cb = cb
        self.data_type = getattr(cb, "data_type", "json.loads")
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
            msg.data = json.loads(msg.data.decode())
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
