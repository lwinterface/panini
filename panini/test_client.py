import time
import json
import random
import typing
from urllib.parse import urljoin

import requests
from pynats import NATSClient, NATSMessage

from panini.utils.helper import start_process


# Annotations for `Session.request()`
Cookies = typing.Union[
    typing.MutableMapping[str, str], requests.cookies.RequestsCookieJar
]
Params = typing.Union[bytes, typing.MutableMapping[str, str]]
DataType = typing.Union[bytes, typing.MutableMapping[str, str], typing.IO]
TimeOut = typing.Union[float, typing.Tuple[float, float]]
FileType = typing.MutableMapping[str, typing.IO]
AuthType = typing.Union[
    typing.Tuple[str, str],
    requests.auth.AuthBase,
    typing.Callable[[requests.Request], requests.Request],
]


class HTTPSessionTestClient(requests.Session):
    __test__ = False

    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        super(HTTPSessionTestClient, self).__init__()
        self.base_url = base_url

    def request(  # type: ignore
        self,
        method: str,
        url: str,
        params: Params = None,
        data: DataType = None,
        headers: typing.MutableMapping[str, str] = None,
        cookies: Cookies = None,
        files: FileType = None,
        auth: AuthType = None,
        timeout: TimeOut = None,
        allow_redirects: bool = None,
        proxies: typing.MutableMapping[str, str] = None,
        hooks: typing.Any = None,
        stream: bool = None,
        verify: typing.Union[bool, str] = None,
        cert: typing.Union[str, typing.Tuple[str, str]] = None,
        json: typing.Any = None,
    ) -> requests.Response:
        url = urljoin(self.base_url, url)
        return super().request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert,
            json=json,
        )


class TestClient:
    __test__ = False

    def __init__(
        self,
        run_panini: typing.Callable = lambda *args, **kwargs: None,
        use_web_server: bool = False,
        base_web_server_url: str = "http://127.0.0.1:8080",
        base_nats_url: str = "nats://127.0.0.1:4222",
        socket_timeout: int = 2,
        name: str = "__".join(
            [
                "test_client",
                str(random.randint(1, 10000000)),
                str(random.randint(1, 10000000)),
            ]
        ),
    ):
        self.run_panini = run_panini
        self.nats_client = NATSClient(
            url=base_nats_url,
            name=name,
            socket_timeout=socket_timeout,
        )
        self.nats_client.connect()

        if use_web_server:
            self.http_session = HTTPSessionTestClient(base_url=base_web_server_url)

        self.panini_process = None

    def __del__(self):
        self.nats_client.close()
        if self.panini_process:
            self.panini_process.kill()
        if hasattr(self, "http_session"):
            self.http_session.close()

    @staticmethod
    def _dict_to_bytes(message: dict) -> bytes:
        return json.dumps(message).encode("utf-8")

    @staticmethod
    def _bytes_to_dict(payload: bytes) -> dict:
        return json.loads(payload)

    def start(
        self, is_sync: bool = False, sleep_time: float = None, is_daemon: bool = None
    ):
        if is_daemon is None:
            is_daemon = False if is_sync else True

        self.panini_process = start_process(self.run_panini, daemon=is_daemon)
        if sleep_time is None:
            time.sleep(6) if is_sync else time.sleep(1)
        else:
            time.sleep(sleep_time)
        return self

    def publish(self, subject: str, message: dict, reply: str = "") -> None:
        self.nats_client.publish(
            subject=subject, payload=self._dict_to_bytes(message), reply=reply
        )

    def request(self, subject: str, message: dict) -> dict:
        return self._bytes_to_dict(
            self.nats_client.request(
                subject=subject, payload=self._dict_to_bytes(message)
            ).payload
        )

    def subscribe(
        self,
        subject: str,
        callback: typing.Callable,
        queue: str = "",
        max_messages: typing.Optional[int] = None,
    ):
        return self.nats_client.subscribe(
            subject=subject,
            callback=callback,
            queue=queue,
            max_messages=max_messages,
        )

    def wait(self, count: int) -> None:
        self.nats_client.wait(count=count)

    def listen(self, subject: str):
        def decorator(func):
            assert isinstance(subject, str)

            def wrapper(incoming_response):
                assert isinstance(incoming_response, NATSMessage)
                wrapper_response = func(
                    subject=incoming_response.subject,
                    message=self._bytes_to_dict(incoming_response.payload),
                )
                if wrapper_response is not None and incoming_response.reply != "":
                    self.publish(
                        subject=incoming_response.reply, message=wrapper_response
                    )
                    self.wait(count=1)

            self.subscribe(subject, wrapper)

            return wrapper

        return decorator
