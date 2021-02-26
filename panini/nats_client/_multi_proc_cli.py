import os
import json
import uuid
import time
import asyncio
from itertools import cycle
from queue import Empty
from types import CoroutineType
from nats.aio.client import Client as NATS
from ._nats_client_interface import NATSClientInterface
from ..utils.logger import get_logger
from ..utils.helper import (
    start_thread,
    start_process,
    is_json,
    validate_msg,
    register_msg,
)
from ._redis_response import RedisResponse, RedisQueue

isr_log = get_logger("inter_services_request")

LISTEN_FOR_NEW_SUBSCRIPTION_SUBJECT = (
    os.environ["CLIENT_ID"]
    if "CLIENT_ID" in os.environ
    else str(uuid.uuid4())[10:] + "__new_subscription "
)


def transform_subject(subject, client_id=None, keyword=""):
    return ".".join(
        [
            client_id if client_id else os.environ["CLIENT_ID"],
            subject.split(".")[-1],
            keyword,
        ]
    )


class _MultiProcNATSClient(NATSClientInterface):
    """
    Sub interface for NATSClient, create additional processes for sending and listening
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
        self.listen_message_queue = {}
        # [self.listen_message_queue.update({subject: multiprocessing.Queue()}) for subject in self.listen_subjects_callbacks]
        [
            self.listen_message_queue.update(
                {
                    subject: RedisQueue(
                        transform_subject(subject, self.client_id, "listener")
                    )
                }
            )
            for subject in self.listen_subjects_callbacks
        ]
        self.publish_message_queue = {}
        [
            self.publish_message_queue.update(
                {
                    transform_subject(
                        "queue" + str(i), self.client_id, "publisher"
                    ): RedisResponse(
                        transform_subject("queue" + str(i), self.client_id, "publisher")
                    )
                }
            )
            for i in range(self.num_of_queues)
        ]
        self.publish_queue_circle = cycle(list(self.publish_message_queue.values()))
        global LISTEN_FOR_NEW_SUBSCRIPTION_SUBJECT
        LISTEN_FOR_NEW_SUBSCRIPTION_SUBJECT = (
            self.client_id
            if hasattr(self, "client_id")
            else str(uuid.uuid4())[10:] + "__new_subscription"
        )
        self.new_listen_subjects_redis_queue = RedisQueue(
            transform_subject(LISTEN_FOR_NEW_SUBSCRIPTION_SUBJECT)
        )
        self.forced_closure = False
        self.nats_listener_process = None
        self.nats_sender_process = None
        self._launch()

    def _launch(self):
        self.nats_listener_process = self._launch_listener()
        self.nats_sender_process = self._launch_sender()
        for subject, q in self.listen_message_queue.items():
            start_thread(self._listen_incoming_messages_forever, args=(q, subject))

    async def aio_subscribe_new_subject(self, subject: str, callback: CoroutineType):
        self.subscribe_new_subject(subject, callback)

    def subscribe_new_subject(self, subject: str, callback: CoroutineType):
        # TODO: include all "subject_include" rules
        if subject not in self.listen_subjects_callbacks:
            self.listen_subjects_callbacks[subject] = []
        self.listen_subjects_callbacks[subject].append(callback)
        q = RedisQueue(subject)
        self.listen_message_queue.update({subject: q})
        self.new_listen_subjects_redis_queue.put(subject)
        start_thread(self._listen_incoming_messages_forever, args=(q, subject))

    def _launch_listener(self):
        listen_queue_subjects = list(self.listen_message_queue.keys())
        return start_process(
            _ListenerProc,
            kwargs={
                "client_id": self.client_id,
                "host": self.host,
                "port": self.port,
                "listen_queue_subjects": listen_queue_subjects,
                "allow_reconnect": self.allow_reconnect,
                "max_reconnect_attempts": self.max_reconnect_attempts,
                "reconnecting_time_wait": self.reconnecting_time_wait,
            },
            daemon=False,
        )

    def _launch_sender(self):
        publish_queue_subjects = list(self.publish_message_queue.keys())
        return start_process(
            _SenderProc,
            kwargs={
                "client_id": self.client_id,
                "host": self.host,
                "port": self.port,
                "publish_queue_subjects": publish_queue_subjects,
                "allow_reconnect": self.allow_reconnect,
                "max_reconnect_attempts": self.max_reconnect_attempts,
                "reconnecting_time_wait": self.reconnecting_time_wait,
            },
            daemon=False,
        )

    def _listen_incoming_messages_forever(self, shared_queue: RedisQueue, subject: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self.forced_closure is False:
            try:
                new_msg = shared_queue.get()
                if new_msg is None:
                    continue
                new_msg = json.loads(new_msg.decode())
                base_subject = new_msg.pop("base_subject")
                if "reply" in new_msg:
                    reply_key = new_msg.pop("reply")
                    # isr_log.info(f"3RECIEVED REQUEST msg: {new_msg['message']}, {base_subject}")
                callbacks = self.listen_subjects_callbacks[base_subject]
                for callback in callbacks:
                    reply = callback(**new_msg)
                    if "reply_key" in locals():
                        if type(reply) is dict:
                            reply = json.dumps(reply)
                        else:
                            reply = str(reply)
                        # isr_log.info(f"4SENDING RESPONSE msg: {new_msg['message']} {base_subject}")
                        RedisResponse(reply_key).put(str(reply))
            except Empty:
                pass
            except Exception as e:
                if "reply" not in locals():
                    reply = "hasn't handled"
                if "new_msg" not in locals():
                    new_msg = "hasn't handled"
                error = f"incoming message handling error {str(e)}, reply: {reply}, new_msg type: {type(new_msg)} new_msg: {new_msg}"
                isr_log.error(error, slack=True)

    def publish_sync(self, subject: str, message, reply_to: str = None):
        if reply_to:
            self._publish_request_with_reply_to_another_subject(
                subject, message, reply_to
            )
            return

        if type(message) == str and is_json(message):
            message = json.loads(message)
        message["subject"] = subject
        message = json.dumps(message)
        q = self.publish_queue_circle.__next__()
        # isr_log.info(f'1BPUBLISH', subject=subject,
        #         redis_subject=transform_subject(subject))
        q.put(message)

    def request_sync(
        self, subject: str, message, timeout: int = 10, unpack: bool = True
    ):
        try:
            reply = str(uuid.uuid4())[10:]
            redis_response = RedisResponse(reply)
            if type(message) == dict:
                message["reply"] = reply
                message["timeout"] = timeout
            elif type(message) == str and is_json(message):
                message = json.loads(message)
                message["reply"] = reply
                message["timeout"] = timeout
            # isr_log.info(f'1BRREQUEST reply {reply} timeout {timeout}', phase='request', subject=subject,
            # redis_subject=transform_subject(subject))
            self.publish_sync(subject, message)
            response = redis_response.return_response_when_appeared(
                subject=reply, timeout=timeout
            )
            # isr_log.info(f'6ARREQUEST reply {reply}', phase='response', subject=subject)
            if unpack:
                return json.loads(response.decode())
            return response.decode()
        except Exception as e:
            isr_log.error(
                f"6ERROR reply {reply} " + str(e),
                from_="PublishClientInterface.publish_request",
                subject=subject,
                request=str(message),
            )

    def _publish_request_with_reply_to_another_subject(
        self, subject: str, message, reply_to: str = None
    ):
        if is_json(message):
            message = json.loads(message)
            message["reply_to"] = reply_to
        else:
            message["reply_to"] = reply_to
        message["subject"] = subject
        message = json.dumps(message)
        q = self.publish_queue_circle.__next__()
        q.put(message)

    async def publish(
        self, subject: str, message, reply_to: str = None, force: bool = None
    ):
        self.publish_sync(subject, message, reply_to)

    async def request(
        self, subject: str, message, timeout: int = 10, unpack: bool = True
    ):
        return self.request_sync(subject, message, timeout=timeout, unpack=unpack)

    def disconnect(self):
        raise NotImplementedError

    def check_connection(self):
        raise NotImplementedError


class _ListenerProc:
    def __init__(
        self,
        client_id: str,
        host: str,
        port: int,
        listen_queue_subjects: list,
        allow_reconnect: bool,
        max_reconnect_attempts: int,
        reconnecting_time_wait: int,
    ):
        self.client_id = client_id
        self.role = "listener"
        self.listen_queue_subjects = listen_queue_subjects
        self.loop = asyncio.get_event_loop()
        self.client = NATS()
        self.loop.run_until_complete(
            self.client.connect(
                host + ":" + str(port),
                loop=self.loop,
                name=self.client_id + "__" + self.role,
            )
        )
        self.connected = True
        isr_log.info("connected " + self.role)
        self.loop.run_until_complete(self.subscribe_all())
        self.loop.create_task(
            self.listen_for_new_subscription(LISTEN_FOR_NEW_SUBSCRIPTION_SUBJECT)
        )
        self.loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(self.loop)))

    async def subscribe_all(self):
        if self.connected:
            for subject in self.listen_queue_subjects:
                await self.subscribe(subject)

    async def subscribe(self, subject: str):
        redis_subject = transform_subject(subject, self.client_id, self.role)
        redis_q = RedisQueue(redis_subject)
        wrapped_callback = self.wrap_callback(subject, redis_q, self.client)
        await self.client.subscribe(
            subject, cb=wrapped_callback, pending_bytes_limit=65536 * 1024 * 10
        )

    async def listen_for_new_subscription(self, subject: str):
        try:
            new_subscription_queue = RedisResponse(subject)
            while True:
                if new_subscription_queue.empty() is True:
                    await asyncio.sleep(0.1)
                    continue
                new_subject_raw = new_subscription_queue.get()
                new_subject = new_subject_raw.decode()
                await self.subscribe(new_subject)
        except Exception as e:
            isr_log.error(
                f"_handle_subject_queue_forever error {os.environ['SERVICE_NAME']}: "
                + str(e)
            )

    @staticmethod
    def wrap_callback(base_subject: str, q: RedisQueue, cli):
        async def wrapped_callback(msg):
            subject = msg.subject
            reply = msg.reply
            data = json.loads(msg.data.decode())
            if reply == "" and not "reply_to" in data:
                q.put(
                    json.dumps(
                        dict(base_subject=base_subject, subject=subject, message=data)
                    )
                )
            elif "reply_to" in data:
                reply_to = data.pop("reply_to")
                q.put(
                    json.dumps(
                        dict(
                            base_subject=base_subject,
                            subject=subject,
                            message=data,
                            reply=reply,
                        )
                    )
                )
                redis_response = RedisResponse(reply)
                response = redis_response.return_response_when_appeared(
                    subject=base_subject
                )
                try:
                    await cli.publish(reply_to, response)
                except Exception as e:
                    isr_log.error(f"ERROR: {str(e)}, message: {data}", slack=True)
            else:
                q.put(
                    json.dumps(
                        dict(
                            base_subject=base_subject,
                            subject=subject,
                            message=data,
                            reply=reply,
                        )
                    )
                )
                redis_response = RedisResponse(reply)
                response = redis_response.return_response_when_appeared(
                    subject=base_subject
                )
                try:
                    await cli.publish(reply, response)
                except Exception as e:
                    isr_log.error(f"ERROR: {str(e)}, message: {data}", slack=True)

        return wrapped_callback


class _SenderProc:
    def __init__(
        self,
        client_id: str,
        host: str,
        port: int,
        publish_queue_subjects: list,
        allow_reconnect: bool,
        max_reconnect_attempts: int,
        reconnecting_time_wait: int,
    ):
        self.client_id = client_id
        self.role = "publisher"
        self.client = NATS()
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(
            self.client.connect(
                host + ":" + str(port),
                loop=self.loop,
                name=self.client_id + "__" + self.role,
                allow_reconnect=allow_reconnect,
                max_reconnect_attempts=max_reconnect_attempts,
                reconnect_time_wait=reconnecting_time_wait,
            )
        )
        isr_log.info("connected " + self.role)
        self.connected = True
        self.run_publish_handlers(publish_queue_subjects)

    def run_publish_handlers(self, publish_queue_subjects: list):
        while self.connected is False:
            time.sleep(1)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run_publish_handlers(publish_queue_subjects))

    async def _run_publish_handlers(self, redis_subjects: list):
        try:
            if not redis_subjects:
                return
            blocking_tasks = [
                self._handle_subject_queue_forever(rt) for rt in redis_subjects
            ]
            await asyncio.wait(blocking_tasks)
        except Exception as e:
            isr_log.error(
                f"ERROR _run_publish_handlers {os.environ['SERVICE_NAME']}: {str(e)}"
            )

    async def _handle_subject_queue_forever(self, redis_queue_name: str):
        try:
            publish_message_queue = RedisResponse(redis_queue_name)
            while True:
                if publish_message_queue.empty() is True:
                    await asyncio.sleep(0.005)
                    continue
                message = publish_message_queue.get(timeout=1)
                message = message.decode()
                await self._send(redis_queue_name, message)
        except Exception as e:
            isr_log.error(
                f"_handle_subject_queue_forever error {self.client_id}: " + str(e)
            )

    async def _send(self, redis_queue_name: str, message):
        try:
            if validate_msg(message):
                if type(message) == str:
                    message = json.loads(message)
                subject = message.pop("subject")

                if "reply" in message:
                    try:
                        reply = message.pop("reply")
                        r = RedisResponse(reply)
                        if reply is False:
                            try:
                                await self.client.publish(subject, message.encode())
                                return
                            except Exception as e:
                                isr_log.error(
                                    f"sending NATS error: {str(e)}",
                                    phase="request",
                                    subject=subject,
                                    redis_subject=redis_queue_name,
                                )
                        timeout = message.pop("timeout", 10)
                        isr_id = reply
                        message = register_msg(message, isr_id)
                        # isr_log(f'2REQUEST: isr_id: {isr_id} message: {message} subject: {subject} timeout {timeout}', phase='request')#, subject=subject, subject=redis_subject)
                        response = await self.client.request(
                            subject, message.encode(), timeout=timeout
                        )
                        # isr_log(f"5RESPONSE: isr_id: {isr_id} subject: {subject} response:"+str(response.data[:300]), phase='response')#, subject=subject, subject=redis_subject)
                        r.put(response.data)
                    except Exception as e:
                        if "isr_log" in locals():
                            isr_log.error(f"4ERROR isr_id: {isr_id} {message}")
                        isr_log.error(
                            f"Invalid message: {message}, error: {str(e)}",
                            phase="request",
                            redis_subject=redis_queue_name,
                            slack=True,
                        )
                else:
                    # isr_log(f'2PUBLISH: message: {message} subject: {subject} ')
                    # self.loop.call_soon(self.client.publish(subject, json.dumps(message).encode()))
                    await self.client.publish(subject, json.dumps(message).encode())
            else:
                isr_log.error(
                    f"Invalid message: {message}",
                    phase="request",
                    redis_subject=redis_queue_name,
                )
        except Exception as e:
            isr_log.exception("Request error :" + str(e), slack=True)
