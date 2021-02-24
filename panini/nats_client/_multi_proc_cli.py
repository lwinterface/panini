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

LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC = (
    os.environ["CLIENT_ID"]
    if "CLIENT_ID" in os.environ
    else str(uuid.uuid4())[10:] + "__new_subscription "
)


def transform_topic(topic, client_id=None, keyword=""):
    return ".".join(
        [
            client_id if client_id else os.environ["CLIENT_ID"],
            topic.split(".")[-1],
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
            listen_topics_callbacks: dict,
            allow_reconnect: bool or None,
            max_reconnect_attempts: int = 60,
            reconnecting_time_wait: int = 2,
            publish_topics=[],
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
        self.listen_message_queue = {}
        # [self.listen_message_queue.update({topic: multiprocessing.Queue()}) for topic in self.listen_topics_callbacks]
        [
            self.listen_message_queue.update(
                {topic: RedisQueue(transform_topic(topic, self.client_id, "listener"))}
            )
            for topic in self.listen_topics_callbacks
        ]
        self.publish_message_queue = {}
        [
            self.publish_message_queue.update(
                {
                    transform_topic(
                        "queue" + str(i), self.client_id, "publisher"
                    ): RedisResponse(
                        transform_topic("queue" + str(i), self.client_id, "publisher")
                    )
                }
            )
            for i in range(self.num_of_queues)
        ]
        self.publish_queue_circle = cycle(list(self.publish_message_queue.values()))
        global LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC
        LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC = (
            self.client_id
            if hasattr(self, "client_id")
            else str(uuid.uuid4())[10:] + "__new_subscription"
        )
        self.new_listen_topics_redis_queue = RedisQueue(
            transform_topic(LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC)
        )
        self.forced_closure = False
        self.nats_listener_process = None
        self.nats_sender_process = None
        self._launch()

    def _launch(self):
        self.nats_listener_process = self._launch_listener()
        self.nats_sender_process = self._launch_sender()
        for topic, q in self.listen_message_queue.items():
            start_thread(self._listen_incoming_messages_forever, args=(q, topic))

    async def aio_subscribe_new_topic(self, topic: str, callback: CoroutineType):
        self.subscribe_new_topic(topic, callback)

    def subscribe_new_topic(self, topic: str, callback: CoroutineType):
        # TODO: include all "topic_include" rules
        if topic not in self.listen_topics_callbacks:
            self.listen_topics_callbacks[topic] = []
        self.listen_topics_callbacks[topic].append(callback)
        q = RedisQueue(topic)
        self.listen_message_queue.update({topic: q})
        self.new_listen_topics_redis_queue.put(topic)
        start_thread(self._listen_incoming_messages_forever, args=(q, topic))

    def _launch_listener(self):
        listen_queue_topics = list(self.listen_message_queue.keys())
        return start_process(
            _ListenerProc,
            kwargs={
                "client_id": self.client_id,
                "host": self.host,
                "port": self.port,
                "listen_queue_topics": listen_queue_topics,
                "allow_reconnect": self.allow_reconnect,
                "max_reconnect_attempts": self.max_reconnect_attempts,
                "reconnecting_time_wait": self.reconnecting_time_wait,
            },
            daemon=False,
        )

    def _launch_sender(self):
        publish_queue_topics = list(self.publish_message_queue.keys())
        return start_process(
            _SenderProc,
            kwargs={
                "client_id": self.client_id,
                "host": self.host,
                "port": self.port,
                "publish_queue_topics": publish_queue_topics,
                "allow_reconnect": self.allow_reconnect,
                "max_reconnect_attempts": self.max_reconnect_attempts,
                "reconnecting_time_wait": self.reconnecting_time_wait,
            },
            daemon=False,
        )

    def _listen_incoming_messages_forever(self, shared_queue: RedisQueue, topic: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self.forced_closure is False:
            try:
                new_msg = shared_queue.get()
                if new_msg is None:
                    continue
                new_msg = json.loads(new_msg.decode())
                base_topic = new_msg.pop("base_topic")
                if "reply" in new_msg:
                    reply_key = new_msg.pop("reply")
                    # isr_log.info(f"3RECIEVED REQUEST msg: {new_msg['message']}, {base_topic}")
                callbacks = self.listen_topics_callbacks[base_topic]
                for callback in callbacks:
                    reply = callback(**new_msg)
                    if "reply_key" in locals():
                        if type(reply) is dict:
                            reply = json.dumps(reply)
                        else:
                            reply = str(reply)
                        # isr_log.info(f"4SENDING RESPONSE msg: {new_msg['message']} {base_topic}")
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

    def publish_sync(self, topic: str, message, reply_to: str = None):
        if reply_to:
            self._publish_request_with_reply_to_another_topic(topic, message, reply_to)
            return

        if type(message) == str and is_json(message):
            message = json.loads(message)
        message["topic"] = topic
        message = json.dumps(message)
        q = self.publish_queue_circle.__next__()
        # isr_log.info(f'1BPUBLISH', topic=topic,
        #         redis_topic=transform_topic(topic))
        q.put(message)

    def request_sync(self, topic: str, message, timeout: int = 10, unpack: bool = True):
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
            # isr_log.info(f'1BRREQUEST reply {reply} timeout {timeout}', phase='request', topic=topic,
            # redis_topic=transform_topic(topic))
            self.publish_sync(topic, message)
            response = redis_response.return_response_when_appeared(
                topic=reply, timeout=timeout
            )
            # isr_log.info(f'6ARREQUEST reply {reply}', phase='response', topic=topic)
            if unpack:
                return json.loads(response.decode())
            return response.decode()
        except Exception as e:
            isr_log.error(
                f"6ERROR reply {reply} " + str(e),
                from_="PublishClientInterface.publish_request",
                topic=topic,
                request=str(message),
            )

    def _publish_request_with_reply_to_another_topic(
            self, topic: str, message, reply_to: str = None
    ):
        if is_json(message):
            message = json.loads(message)
            message["reply_to"] = reply_to
        else:
            message["reply_to"] = reply_to
        message["topic"] = topic
        message = json.dumps(message)
        q = self.publish_queue_circle.__next__()
        q.put(message)

    async def publish(
            self, topic: str, message, reply_to: str = None, force: bool = None
    ):
        self.publish_sync(topic, message, reply_to)

    async def request(
            self, topic: str, message, timeout: int = 10, unpack: bool = True
    ):
        return self.request_sync(topic, message, timeout=timeout, unpack=unpack)

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
            listen_queue_topics: list,
            allow_reconnect: bool,
            max_reconnect_attempts: int,
            reconnecting_time_wait: int,
    ):
        self.client_id = client_id
        self.role = "listener"
        self.listen_queue_topics = listen_queue_topics
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
            self.listen_for_new_subscription(LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC)
        )
        self.loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(self.loop)))

    async def subscribe_all(self):
        if self.connected:
            for topic in self.listen_queue_topics:
                await self.subscribe(topic)

    async def subscribe(self, topic: str):
        redis_topic = transform_topic(topic, self.client_id, self.role)
        redis_q = RedisQueue(redis_topic)
        wrapped_callback = self.wrap_callback(topic, redis_q, self.client)
        await self.client.subscribe(
            topic, cb=wrapped_callback, pending_bytes_limit=65536 * 1024 * 10
        )

    async def listen_for_new_subscription(self, topic: str):
        try:
            new_subscription_queue = RedisResponse(topic)
            while True:
                if new_subscription_queue.empty() is True:
                    await asyncio.sleep(0.1)
                    continue
                new_topic_raw = new_subscription_queue.get()
                new_topic = new_topic_raw.decode()
                await self.subscribe(new_topic)
        except Exception as e:
            isr_log.error(
                f"_handle_topic_queue_forever error {os.environ['SERVICE_NAME']}: "
                + str(e)
            )

    @staticmethod
    def wrap_callback(base_topic: str, q: RedisQueue, cli):
        async def wrapped_callback(msg):
            subject = msg.subject
            reply = msg.reply
            data = json.loads(msg.data.decode())
            if reply == "" and not "reply_to" in data:
                q.put(
                    json.dumps(dict(base_topic=base_topic, topic=subject, message=data))
                )
            elif "reply_to" in data:
                reply_to = data.pop("reply_to")
                q.put(
                    json.dumps(
                        dict(
                            base_topic=base_topic,
                            topic=subject,
                            message=data,
                            reply=reply,
                        )
                    )
                )
                redis_response = RedisResponse(reply)
                response = redis_response.return_response_when_appeared(
                    topic=base_topic
                )
                try:
                    await cli.publish(reply_to, response)
                except Exception as e:
                    isr_log.error(f"ERROR: {str(e)}, message: {data}", slack=True)
            else:
                q.put(
                    json.dumps(
                        dict(
                            base_topic=base_topic,
                            topic=subject,
                            message=data,
                            reply=reply,
                        )
                    )
                )
                redis_response = RedisResponse(reply)
                response = redis_response.return_response_when_appeared(
                    topic=base_topic
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
            publish_queue_topics: list,
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
        self.run_publish_handlers(publish_queue_topics)

    def run_publish_handlers(self, publish_queue_topics: list):
        while self.connected is False:
            time.sleep(1)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run_publish_handlers(publish_queue_topics))

    async def _run_publish_handlers(self, redis_topics: list):
        try:
            if not redis_topics:
                return
            blocking_tasks = [
                self._handle_topic_queue_forever(rt) for rt in redis_topics
            ]
            await asyncio.wait(blocking_tasks)
        except Exception as e:
            isr_log.error(
                f"ERROR _run_publish_handlers {os.environ['SERVICE_NAME']}: {str(e)}"
            )

    async def _handle_topic_queue_forever(self, redis_queue_name: str):
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
                f"_handle_topic_queue_forever error {self.client_id}: " + str(e)
            )

    async def _send(self, redis_queue_name: str, message):
        try:
            if validate_msg(message):
                if type(message) == str:
                    message = json.loads(message)
                topic = message.pop("topic")

                if "reply" in message:
                    try:
                        reply = message.pop("reply")
                        r = RedisResponse(reply)
                        if reply is False:
                            try:
                                await self.client.publish(topic, message.encode())
                                return
                            except Exception as e:
                                isr_log.error(
                                    f"sending NATS error: {str(e)}",
                                    phase="request",
                                    topic=topic,
                                    redis_topic=redis_queue_name,
                                )
                        timeout = message.pop("timeout", 10)
                        isr_id = reply
                        message = register_msg(message, isr_id)
                        # isr_log(f'2REQUEST: isr_id: {isr_id} message: {message} topic: {topic} timeout {timeout}', phase='request')#, topic=topic, redis_topic=redis_topic)
                        response = await self.client.request(
                            topic, message.encode(), timeout=timeout
                        )
                        # isr_log(f"5RESPONSE: isr_id: {isr_id} topic: {topic} response:"+str(response.data[:300]), phase='response')#, topic=topic, redis_topic=redis_topic)
                        r.put(response.data)
                    except Exception as e:
                        if "isr_log" in locals():
                            isr_log.error(f"4ERROR isr_id: {isr_id} {message}")
                        isr_log.error(
                            f"Invalid message: {message}, error: {str(e)}",
                            phase="request",
                            redis_topic=redis_queue_name,
                            slack=True,
                        )
                else:
                    # isr_log(f'2PUBLISH: message: {message} topic: {topic} ')
                    # self.loop.call_soon(self.client.publish(topic, json.dumps(message).encode()))
                    await self.client.publish(topic, json.dumps(message).encode())
            else:
                isr_log.error(
                    f"Invalid message: {message}",
                    phase="request",
                    redis_topic=redis_queue_name,
                )
        except Exception as e:
            isr_log.exception("Request error :" + str(e), slack=True)
