import json
from typing import Callable, Optional

from pynats import NATSClient, NATSMessage
from anthill.utils.helper import start_process


class Sandbox:
    def __init__(self, app):
        start_process(app.start)
        self.nats_client = NATSClient()
        self.nats_client.connect()

    @staticmethod
    def _dict_to_bytes(message: dict) -> bytes:
        return json.dumps(message).encode('utf-8')

    @staticmethod
    def _bytes_to_dict(payload: bytes) -> dict:
        return json.loads(payload)

    def publish(self, topic: str, message: dict, reply: str = "") -> None:
        self.nats_client.publish(subject=topic, payload=self._dict_to_bytes(message), reply=reply)

    def request(self, topic: str, message: dict) -> dict:
        return self._bytes_to_dict(
            self.nats_client.request(subject=topic, payload=self._dict_to_bytes(message)).payload
        )

    def subscribe(
            self,
            topic: str,
            callback: Callable,
            queue: str = "",
            max_messages: Optional[int] = None,
    ):
        return self.nats_client.subscribe(
            subject=topic,
            callback=callback,
            queue=queue,
            max_messages=max_messages,
        )

    def wait(self, count: int) -> None:
        self.nats_client.wait(count=count)

    def handler(self, func):
        def wrapper(response):
            assert isinstance(response, NATSMessage)
            func(topic=response.subject, message=self._bytes_to_dict(response.payload))

        return wrapper







