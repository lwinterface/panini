import asyncio
import json
import random
import time

from nats.aio.client import Client as NATS

from anthill.app import App
from anthill.utils.helper import start_process


class TestClientEmulator:

    def __init__(self,
                 filepath: str,
                 anthill_app: App,
                 emulate_timeout=True,
                 compare_output=False,
                 ignore_map=None,
                 url: str = 'nats://127.0.0.1:4222',
                 socket_timeout: int = 2,
                 name: str = '__'.join(
                     ['emulator', str(random.randint(1, 10000000)), str(random.randint(1, 10000000))]
                 )):

        # super().__init__(anthill_app, url, socket_timeout, name)
        self._filepath = filepath
        self._anthill_app = anthill_app
        self._publish_queue = []
        self._listen_queues = {}
        self._emulate_timeout = emulate_timeout
        self._compare_output = compare_output
        self._ignore_map = ignore_map
        self._client = NATS()
        self._load()

        self._subs = []

    def _load(self):
        last_response_event = {}
        last_request_event = {}
        with open(self._filepath) as file:
            for line in file.readlines():
                event = json.loads(line)

                # input
                if event["message_type"] == "listen":
                    self._publish_queue.append(event)

                if event["message_type"] == "listen_request":
                    last_request_event = event

                if event["message_type"] == "request":
                    last_request_event["request"] = event
                    self._publish_queue.append(last_request_event)

                # output
                if event["message_type"] == "publish":
                    if event["topic"] not in self._listen_queues:
                        self._listen_queues[event["topic"]] = []

                    self._listen_queues[event["topic"]].append(last_response_event)

                elif event["message_type"] == "publish_response":
                    last_response_event = event

                elif event["message_type"] == "response":
                    last_response_event["response"] = event

                    if event["topic"] not in self._listen_queues:
                        self._listen_queues[event["topic"]] = []

                    self._listen_queues[event["topic"]].append(last_response_event)

    def _handle_ignore(self, topic: str, message: dict):
        if not self._ignore_map:
            return message
        ignore_attrs = self._ignore_map["default"] + self._ignore_map.get(topic, [])
        return {key: value for key, value in message.items() if key not in ignore_attrs}

    async def _mock_requests(self, data):
        topic = data.subject
        message = self._bytes_to_dict(data.data)
        reply_to = data.reply
        event = self._listen_queues[topic].pop(0)

        if self._compare_output:
            gotten_message = self._handle_ignore(topic, message)
            expected_message = self._handle_ignore(topic, event["message"])

            assert gotten_message == expected_message

        if event["message_type"] == "publish_response":
            response_message = event["response"]["message"]
            response_message["isr-id"] = message["isr-id"]
            print("response", response_message)
            # return response_message
            await self._client.publish(reply_to, self._dict_to_bytes(response_message))

    def listen(self, topic: str):
        def decorator(func):
            assert isinstance(topic, str)

            def wrapper(incoming_response):
                wrapper_response = func(topic=incoming_response.subject,
                                        message=self._bytes_to_dict(incoming_response.data))
                if wrapper_response is not None and incoming_response.reply != "":
                    self._client.publish(incoming_response.reply, wrapper_response)

            self._subs.append([topic, wrapper])
            # self._client.subscribe()

            return wrapper

        return decorator

    async def run(self):
        start_process(self._anthill_app.start, daemon=True)
        await asyncio.sleep(4)
        await self._client.connect()

        for topic in self._listen_queues:
            await self._client.subscribe(topic, cb=self._mock_requests)

        for sub in self._subs:
            await self._client.subscribe(sub[0], cb=sub[1])

        await self.run_publish()

        while sum(len(queue) for queue in self._listen_queues.values()) > 0:
            await asyncio.sleep(0.1)

    async def run_publish(self):
        last_timestamp = None
        while len(self._publish_queue) > 0:
            event = self._publish_queue.pop(0)
            if event["message_type"] == "listen":
                print("publish", event["topic"], event["message"])
                await self._client.publish(event["topic"], self._dict_to_bytes(event["message"]))
            elif event["message_type"] == "listen_request":
                print("publish_request", event["topic"], event["message"])
                result = await self._client.request(event["topic"], self._dict_to_bytes(event["message"]), timeout=5)
                print("response", result)
                if self._compare_output:
                    gotten_message = self._handle_ignore(event["topic"], result)
                    expected_message = self._handle_ignore(event["topic"], event["request"]["message"])

                    assert gotten_message == expected_message

            if not self._emulate_timeout:
                continue

            if last_timestamp:
                wait = event["timestamp"] - last_timestamp
                time.sleep(wait)

            last_timestamp = event["timestamp"]

    def _dict_to_bytes(self, message: dict) -> bytes:
        return json.dumps(message).encode('utf-8')

    def _bytes_to_dict(self, payload: bytes) -> dict:
        return json.loads(payload)
