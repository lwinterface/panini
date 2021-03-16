import asyncio
import json
import time

from nats.aio.client import Client as NATS


def _dict_to_bytes(message: dict) -> bytes:
    return json.dumps(message).encode('utf-8')


def _bytes_to_dict(payload: bytes) -> dict:
    return json.loads(payload)


class EmulatorClient:

    def __init__(
        self,
        filepath: str,
        prefix: str = "emulator",
        emulate_timeout: bool = True,
        compare_output: bool = False
    ):
        self._filepath = filepath

        self._publish_queue = []
        self._listen_queues = {}

        self._emulate_timeout = emulate_timeout
        self._compare_output = compare_output
        self._client = NATS()

        self._prefix = prefix
        self._subscriptions = []

        self._load()

    def _load(self):
        with open(self._filepath) as file:
            lines = file.readlines()

        for line in lines:
            event = json.loads(line)
            event_type = event["event_type"]
            subject = self._prefix + "." + event["subject"]
            # subject = event["subject"]

            if event_type.startswith("listen"):
                self._publish_queue.append(event)

            elif event_type.startswith("send"):
                if subject not in self._listen_queues:
                    self._listen_queues[subject] = []

                self._listen_queues[subject].append(event)

    async def _mock_requests(self, data):
        subject = data.subject
        message = _bytes_to_dict(data.data)
        reply_to = data.reply
        event = self._listen_queues[subject].pop(0)

        if self._compare_output:
            assert message == event["message"]

        if event["event_type"] == "listen_request":
            response_message = event["response"]
            response_message["isr-id"] = message["isr-id"]

            # return response_message
            await self._client.publish(reply_to, _dict_to_bytes(response_message))

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

    async def run(self):
        await self._client.connect()

        for subject in self._listen_queues:
            await self._client.subscribe(subject, cb=self._mock_requests)

        for subject, callback in self._subscriptions:
            await self._client.subscribe(subject, cb=callback)

        # publish all the events
        await self.run_publish()

    async def run_publish(self):
        last_timestamp = None
        while len(self._publish_queue) > 0:
            event = self._publish_queue.pop(0)

            event_type = event["event_type"]
            subject = self._prefix + "." + event["subject"]
            timestamp = event["timestamp"]
            message = _dict_to_bytes(event["message"])

            if event_type == "listen_publish":
                await self._client.publish(subject, message)

            elif event_type == "listen_request":
                response = await self._client.request(subject, message, timeout=5)
                if self._compare_output:
                    assert response == event["response"]

            if self._emulate_timeout:
                if last_timestamp:
                    wait = timestamp - last_timestamp
                    time.sleep(wait)

                last_timestamp = timestamp

    async def wait(self, max_timeout: int = None):
        start = time.time()
        while True:
            if sum(len(queue) for queue in self._listen_queues.values()) == 0:
                break

            if max_timeout and time.time() - start > max_timeout:
                break

            await asyncio.sleep(0.1)
