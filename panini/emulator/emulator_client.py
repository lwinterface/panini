import asyncio
import json
import time

from nats.aio.client import Client as NATS

from panini.app import get_app
from panini.nats_client.nats_client_interface import Msg


def _dict_to_bytes(message: dict) -> bytes:
    return json.dumps(message).encode('utf-8')


def _bytes_to_dict(payload: bytes) -> dict:
    return json.loads(payload)


class EmulatorClient:

    def __init__(
            self,
            filepath: str,
            prefix: str,
            emulate_timeout: bool = True,
            compare_output: bool = False
    ):
        self._name = "emulator_client" + prefix
        self._filepath = filepath

        self._publish_queue = []
        self._listen_queues = {}

        self._emulate_timeout = emulate_timeout
        self._compare_output = compare_output
        self._client = NATS()

        self._prefix = prefix
        self._subscriptions = []

        self._is_app_started = False
        self._is_emulator_ready = False

        self._load()

    def _load(self):
        with open(self._filepath) as file:
            lines = file.readlines()

        for line in lines:
            event = json.loads(line)
            event_type = event["event_type"]
            subject = self._prefix + "." + event["subject"]

            if event_type.startswith("listen"):
                self._publish_queue.append(event)

            elif event_type.startswith("send"):
                if subject not in self._listen_queues:
                    self._listen_queues[subject] = []

                self._listen_queues[subject].append(event)

    async def _mock_requests(self, message):
        subject = message.subject
        reply_to = message.reply
        body = _bytes_to_dict(message.data)
        event = self._listen_queues[subject].pop(0)
        if self._compare_output:
            assert body == event["message"], f"'{body}' vs '{event['message']}'"

        if event["event_type"].endswith("request"):
            await self._client.publish(reply_to, _dict_to_bytes(event["response"]))

    def listen(self, subject: str):
        def decorator(func):
            assert isinstance(subject, str)

            def wrapper(incoming_response):
                wrapper_response = func(topic=incoming_response.subject,
                                        message=_bytes_to_dict(incoming_response.data))
                if wrapper_response is not None and incoming_response.reply != "":
                    self._client.publish(incoming_response.reply, wrapper_response)

            self._subscriptions.append([subject, wrapper])

            return wrapper

        return decorator

    def start(self, max_timeout_after_start: float = 20):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._run())
        loop.run_until_complete(self._wait_after(max_timeout_after_start))

    async def _on_app_started(self, message: Msg):
        self._is_app_started = True

    async def _run(self):
        await self._client.connect()

        for subject in self._listen_queues:
            await self._client.subscribe(subject, cb=self._mock_requests)

        for subject, callback in self._subscriptions:
            await self._client.subscribe(subject, cb=callback)

        app = get_app()
        subject = f"{self._prefix}.panini_events.{app.service_name}.{app.client_id}.started"
        await self._client.subscribe(subject, cb=self._on_app_started)

        self._is_emulator_ready = True
        await self._wait_for_app_to_start()
        # publish all the events
        await self._run_publish()

    async def _run_publish(self):
        last_timestamp = None
        while len(self._publish_queue) > 0:
            event = self._publish_queue.pop(0)

            event_type = event["event_type"]
            subject = self._prefix + "." + event["subject"]
            timestamp = event["timestamp"]
            message = _dict_to_bytes(event["message"])

            if event_type.endswith("publish"):
                await self._client.publish(subject, message)

            elif event_type.endswith("request"):
                response = await self._client.request(subject, message, timeout=5)
                if self._compare_output:
                    assert json.loads(response.data) == event["response"]

            if self._emulate_timeout:
                if last_timestamp:
                    wait = timestamp - last_timestamp
                    time.sleep(wait)

                last_timestamp = timestamp

    def wait_for_readiness(self):
        while not self._is_emulator_ready:
            time.sleep(0.1)

    async def _wait_for_app_to_start(self):
        while not self._is_app_started:
            await asyncio.sleep(0.1)

    async def _wait_after(self, max_timeout: float = None):
        start = time.time()
        while True:
            if sum(len(queue) for queue in self._listen_queues.values()) == 0:
                break

            if max_timeout and time.time() - start > max_timeout:
                break

            await asyncio.sleep(0.1)
