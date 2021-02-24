import json
import asyncio
import uuid
from types import CoroutineType
from nats.aio.client import Client as NATS
from ..utils.helper import is_json, run_coro_threadsafe, validate_msg, register_msg
from ..exceptions import EventHandlingError
from ..utils.logger import get_logger
from ._nats_client_interface import NATSClientInterface

log = get_logger("panini")
isr_log = get_logger("inter_services_request")


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
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self._establish_connection())

    async def _establish_connection(self):
        # TODO: authorization
        self.client = NATS()
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
                    await self.aio_subscribe_new_subject(subject, callback)

    def subscribe_new_subject(self, subject: str, callback: CoroutineType):
        self.loop.run_until_complete(self.aio_subscribe_new_subject(subject, callback))

    async def aio_subscribe_new_subject(self, subject: str, callback: CoroutineType):
        wrapped_callback = self.wrap_callback(callback, self)
        await self.client.subscribe(
            subject,
            queue=self.queue,
            cb=wrapped_callback,
            pending_bytes_limit=self.pending_bytes_limit,
        )

    @staticmethod
    def wrap_callback(cb, cli):
        async def wrapped_callback(msg):
            async def callback(cb, subject: str, data, reply_to=None, isr_id=None):
                if asyncio.iscoroutinefunction(cb):

                    async def coro_callback_with_reply(subject, data, reply_to, isr_id):
                        try:
                            reply = await cb(subject, data)
                            if reply_to:
                                if reply is None:
                                    return
                                reply["isr-id"] = isr_id
                                reply = json.dumps(reply)
                                await cli.publish(reply_to, reply)
                        except EventHandlingError as e:
                            if not "reply" in locals():
                                reply = ""
                            raise EventHandlingError(
                                f"callback_when_future_finished ERROR: {str(e)}, reply if exist: {reply}"
                            )

                    try:
                        asyncio.ensure_future(
                            coro_callback_with_reply(subject, data, reply_to, isr_id)
                        )
                        # await coro_callback_with_reply(subject, data, reply_to, isr_id)
                    except EventHandlingError as e:
                        raise Exception(f"callback ERROR: {str(e)}")
                else:
                    return cb(subject, data)

            async def handle_message_with_response(cli, data, reply_to, isr_id):
                reply = await callback(cb, subject, data, reply_to, isr_id)
                if reply:
                    reply["isr-id"] = isr_id
                    reply = json.dumps(reply)
                    await cli.publish(reply_to, reply)

            subject = msg.subject
            raw_data = msg.data.decode()
            data = json.loads(raw_data)
            if not msg.reply == "":
                reply_to = msg.reply
            elif "reply_to" in data:
                reply_to = data.pop("reply_to")
            else:
                await callback(cb, subject, data)
                return
            isr_id = data.get("isr-id", str(uuid.uuid4())[:10])
            try:
                await handle_message_with_response(cli, data, reply_to, isr_id)
            except EventHandlingError as e:
                if not "isr_id" in locals():
                    isr_id = "Absent or Unknown"
                isr_log.error(
                    "4SENDING RESPONSE error msg: " + str(e),
                    subject=subject,
                    isr_id=isr_id,
                )

        return wrapped_callback

    def publish_sync(self, subject: str, message: dict, reply_to: str = None):
        if reply_to is not None:
            return self._publish_request_with_reply_to_another_subject(
                subject, message, reply_to
            )

        asyncio.ensure_future(self.publish(subject, message, reply_to))

    def _publish_request_with_reply_to_another_subject(
        self, subject: str, message: dict, reply_to: str = None
    ):
        asyncio.ensure_future(
            self._aio_publish_request_with_reply_to_another_subject(
                subject, message, reply_to
            )
        )

    def publish_from_another_thread(self, subject: str, message: dict):
        self.loop.call_soon_threadsafe(self.publish, subject, message)

    def request_sync(
        self, subject: str, message: dict, timeout: int = 10, unpack: bool = False
    ):
        asyncio.ensure_future(self.request(subject, message, timeout, unpack))

    def request_from_another_thread(
        self,
        subject: str,
        message,
        loop,
        timeout: int = 10,
        unpack: bool = False,
    ):
        coro = self.request(subject, message, timeout, unpack)
        return loop.run_until_complete(run_coro_threadsafe(coro, self.loop))

    async def publish(
        self,
        subject: str,
        message: dict,
        reply_to: str = None,
        force: bool = False,
        nonjson: bool = False,
    ):
        if reply_to is not None:
            return await self._aio_publish_request_with_reply_to_another_subject(
                subject, message, reply_to
            )

        if type(message) is dict and nonjson is False:
            message = json.dumps(message)
            message = message.encode()
        elif type(message) is str:
            message = message.encode()
        elif type(message) is bytes:
            pass
        if not force:
            await self.client.publish(subject, message)
        else:
            raise NotImplementedError

    async def request(
        self, subject: str, message: dict, timeout: int = 10, unpack: bool = False
    ):
        if type(message) == str:
            message = json.loads(message)
        if validate_msg(message):
            if "isr-id" not in message:
                isr_id = str(uuid.uuid4())
                message = register_msg(message, isr_id)
            else:
                message = json.dumps(message)
            message = message.encode()
            response = await self.client.request(subject, message, timeout=timeout)
            response = response.data
            if unpack:
                response = json.loads(response)
            return response
        isr_log.error(f"Invalid message: {message}", subject=subject)

    async def _aio_publish_request_with_reply_to_another_subject(
        self, subject: str, message, reply_to: str = None
    ):
        message["isr-id"] = str(uuid.uuid4())[:10]
        if is_json(message):
            message = json.loads(message)
            message["reply_to"] = reply_to
        else:
            message["reply_to"] = reply_to
        message = json.dumps(message)
        await self.publish(subject, message)

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
