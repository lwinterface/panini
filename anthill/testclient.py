import time
import json
import random
from typing import Callable, Optional

from pynats import NATSClient, NATSMessage

from anthill.utils.helper import start_process


class TestClient:
    __test__ = False

    def __init__(self,
                 run_anthill: Callable = lambda callback: None,
                 url: str = 'nats://127.0.0.1:4222',
                 socket_timeout: int = 2,
                 name: str = '__'.join(
                     ['test_client', str(random.randint(1, 10000000)), str(random.randint(1, 10000000))]
                 )):
        self.run_anthill = run_anthill
        self.nats_client = NATSClient(
            url=url,
            name=name,
            socket_timeout=socket_timeout,
        )
        self.http_session = None
        self.nats_client.connect()
        self.anthill_process = None

    @staticmethod
    def _dict_to_bytes(message: dict) -> bytes:
        return json.dumps(message).encode('utf-8')

    @staticmethod
    def _bytes_to_dict(payload: bytes) -> dict:
        return json.loads(payload)

    def start(self, is_sync=False):
        is_daemon = False if is_sync else True
        self.anthill_process = start_process(self.run_anthill, daemon=is_daemon)
        time.sleep(4) if is_sync else time.sleep(0.1)
        return self

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

    def listen(self, topic: str):
        def decorator(func):
            assert isinstance(topic, str)

            def wrapper(incoming_response):
                assert isinstance(incoming_response, NATSMessage)
                wrapper_response = func(topic=incoming_response.subject,
                                        message=self._bytes_to_dict(incoming_response.payload))
                if wrapper_response is not None and incoming_response.reply != "":
                    self.publish(topic=incoming_response.reply,
                                 message=wrapper_response)
                    self.wait(count=1)

            self.subscribe(topic, wrapper)

            return wrapper
        return decorator
