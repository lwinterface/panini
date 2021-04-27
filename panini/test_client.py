import os
import shutil
import time
import json
import random
import typing
from urllib.parse import urljoin

import requests
import websocket
from pynats import NATSClient, NATSMessage

from .exceptions import TestClientError
from .utils.helper import start_process
from panini.nats_client import Msg


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


def get_logger_files_path(folder: str = "test_logs", remove_if_exist: bool = False):
    testing_directory_path = os.getcwd()
    testing_logs_directory_path = os.path.join(testing_directory_path, folder)
    if remove_if_exist:
        if os.path.exists(testing_logs_directory_path):
            shutil.rmtree(testing_logs_directory_path)

    return testing_logs_directory_path


class TestClient:
    __test__ = False

    def __init__(
        self,
        run_panini: typing.Callable = lambda *args, **kwargs: None,
        run_panini_args: list = None,
        run_panini_kwargs: dict = None,
        panini_service_name: str = "*",
        panini_client_id: str = "*",
        logger_files_path: str = "test_logs",
        use_web_server: bool = False,
        use_web_socket: bool = False,
        base_web_server_url: str = "http://127.0.0.1:8080",
        base_nats_url: str = "nats://127.0.0.1:4222",
        socket_timeout: int = 5,
        auto_reconnect: bool = True,
        name: str = "__".join(
            [
                "test_client",
                str(random.randint(1, 10000000)),
                str(random.randint(1, 10000000)),
            ]
        ),
    ):
        self.run_panini = run_panini
        self.run_panini_args = run_panini_args or []
        self.run_panini_kwargs = run_panini_kwargs or {}
        self.panini_service_name = panini_service_name
        self.panini_client_id = panini_client_id
        self.logger_files_path = logger_files_path
        self.base_web_server_url = base_web_server_url
        self.use_web_server = use_web_server
        self.use_web_socket = use_web_socket
        self.name = name
        self.base_nats_url = base_nats_url
        self.socket_timeout = socket_timeout
        self.auto_reconnect = auto_reconnect
        self.nats_client = self.create_nats_client()
        self.nats_client.connect()

        if use_web_server:
            self.http_session = HTTPSessionTestClient(base_url=base_web_server_url)

        if use_web_socket:
            self.websocket_session = websocket.WebSocket()

        self.panini_process = None

    def create_nats_client(self) -> NATSClient:
        return NATSClient(
            url=self.base_nats_url,
            name=self.name,
            socket_timeout=self.socket_timeout,
        )

    @staticmethod
    def _dict_to_bytes(message: dict) -> bytes:
        return json.dumps(message).encode("utf-8")

    @staticmethod
    def _bytes_to_dict(payload: bytes) -> dict:
        return json.loads(payload)

    @staticmethod
    def wrap_run_panini(
        run_panini,
        run_panini_args: list,
        run_panini_kwargs: dict,
        logger_files_path: str,
    ):
        from .utils.logger import get_logger

        test_logger = get_logger("panini")
        # set the panini testing data in os.environ
        os.environ["PANINI_TEST_MODE"] = "true"
        testing_logger_files_path = (
            get_logger_files_path(logger_files_path)
            if not os.path.isabs(logger_files_path)
            else logger_files_path
        )

        os.environ["PANINI_TEST_LOGGER_FILES_PATH"] = testing_logger_files_path
        try:
            run_panini(*run_panini_args, **run_panini_kwargs)
        except Exception as e:
            test_logger.exception(f"Run panini error: {e}")

    def start(self, is_sync: bool = False, is_daemon: bool = None):
        if is_daemon is None:
            is_daemon = False if is_sync else True

        @self.listen(
            f"panini_events.{self.panini_service_name}.{self.panini_client_id}.started"
        )
        def panini_started(msg):
            pass

        self.panini_process = start_process(
            self.wrap_run_panini,
            args=(
                self.run_panini,
                self.run_panini_args,
                self.run_panini_kwargs,
                self.logger_files_path,
            ),
            daemon=is_daemon,
        )

        if is_sync:
            time.sleep(5)
        else:
            try:
                self.wait(1)  # wait for panini to start
            except OSError:
                raise TestClientError(
                    "TestClient was waiting panini to start, but panini does not started"
                )

        if self.use_web_server:
            pass  # TODO: understand, why don't we need to wait for web_server

        return self

    def stop(self):
        self.nats_client.close()
        if self.panini_process:
            self.panini_process.kill()
        if hasattr(self, "http_session"):
            self.http_session.close()

        if hasattr(self, "websocket_session"):
            self.websocket_session.close()

    def publish(self, subject: str, message: dict, reply: str = "") -> None:
        self.nats_client.publish(
            subject=subject, payload=self._dict_to_bytes(message), reply=reply
        )

    def request(self, subject: str, message: dict) -> dict:
        if self.auto_reconnect:
            try:
                self.nats_client.ping()
            except Exception:
                self.nats_client.reconnect()

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
                msg = Msg(
                    subject=incoming_response.subject,
                    data=self._bytes_to_dict(incoming_response.payload),
                    reply=incoming_response.reply,
                    sid=incoming_response.sid,
                )
                wrapper_response = func(msg)
                if wrapper_response is not None and incoming_response.reply != "":
                    self.publish(
                        subject=incoming_response.reply, message=wrapper_response
                    )
                    try:
                        self.wait(count=1)
                    except OSError:
                        raise TestClientError(
                            f"TestClient listen subject: {incoming_response.subject},"
                            f"Response was sent, but it was not correctly handled"
                        )

            self.subscribe(subject, wrapper)

            return wrapper

        return decorator
