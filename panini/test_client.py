import os
import shutil
import threading
import json
import random
import typing
from urllib.parse import urljoin

import requests
import websocket
from pynats import NATSClient, NATSMessage

from .exceptions import TestClientError
from .utils.helper import start_process, start_thread
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
        run_panini: typing.Callable = None,
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
        listener_socket_timeout: int = 1,
        auto_reconnect: bool = True,
        name: str = "__".join(
            [
                "test_client",
                str(random.randint(1, 10000000)),
                str(random.randint(1, 10000000)),
            ]
        ),
        _subscribed_subjects: [str] = None,
    ):
        self.run_panini = run_panini
        self.run_panini_args = run_panini_args or []
        self.run_panini_kwargs = run_panini_kwargs or {}
        self._subscribed_subjects = _subscribed_subjects or []
        self.panini_service_name = panini_service_name
        self.panini_client_id = panini_client_id
        self.logger_files_path = logger_files_path
        self.base_web_server_url = base_web_server_url
        self.use_web_server = use_web_server
        self.use_web_socket = use_web_socket
        self.name = name
        self.base_nats_url = base_nats_url
        self.auto_reconnect = auto_reconnect
        self.nats_client_sender = self.create_nats_client("sender", socket_timeout)
        self.nats_client_listener = self.create_nats_client(
            "listener", listener_socket_timeout
        )
        self.nats_client_sender.connect()
        self.nats_client_listener.connect()
        self.nats_client_listener_thread = None
        self.nats_client_listener_thread_stop_event = threading.Event()

        if use_web_server:
            self.http_session = HTTPSessionTestClient(base_url=base_web_server_url)

        if use_web_socket:
            self.websocket_session = websocket.WebSocket()

        self.panini_process = None

    def create_nats_client(self, suffix: str, nats_timeout) -> NATSClient:
        return NATSClient(
            url=self.base_nats_url,
            name=self.name + suffix,
            socket_timeout=nats_timeout,
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
        use_error_middleware: bool,
    ):
        from .utils.logger import get_logger

        test_logger = get_logger("panini")
        # set the panini testing data in os.environ
        os.environ["PANINI_TEST_MODE"] = "true"
        os.environ["PANINI_TEST_MODE_USE_ERROR_MIDDLEWARE"] = (
            "true" if use_error_middleware else "false"
        )
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

    def start(
        self,
        is_daemon: bool = True,
        do_always_listen: bool = True,
        use_error_middleware=True,
    ):
        if do_always_listen and len(self._subscribed_subjects) > 0:

            def nats_listener_worker(stop_event):
                try:
                    while not stop_event.wait(1):
                        self.nats_client_listener.wait()
                except Exception:
                    pass

            # Run nats-listener process
            self.nats_client_listener_thread = start_thread(
                nats_listener_worker,
                args=[self.nats_client_listener_thread_stop_event],
                daemon=True,
            )

        if self.run_panini is not None:

            def panini_started(msg):
                pass

            sub = self.nats_client_sender.subscribe(
                f"panini_events.{self.panini_service_name}.{self.panini_client_id}.started",
                callback=panini_started,
                max_messages=1,
            )
            self.nats_client_sender.auto_unsubscribe(sub)

            self.panini_process = start_process(
                self.wrap_run_panini,
                args=(
                    self.run_panini,
                    self.run_panini_args,
                    self.run_panini_kwargs,
                    self.logger_files_path,
                    use_error_middleware,
                ),
                daemon=is_daemon,
            )

            try:
                self.nats_client_sender.wait(count=1)  # wait for panini to start
            except OSError:
                raise TestClientError(
                    "TestClient was waiting panini to start, but panini does not started"
                )

            if self.use_web_server:
                pass  # TODO: understand, why don't we need to wait for web_server

        return self

    def stop(self):
        self.nats_client_listener.close()
        self.nats_client_sender.close()
        self.nats_client_listener_thread_stop_event.set()

        if self.panini_process:
            self.panini_process.kill()

        if hasattr(self, "http_session"):
            self.http_session.close()

        if hasattr(self, "websocket_session"):
            self.websocket_session.close()

    def publish(self, subject: str, message: dict, reply: str = "") -> None:
        self.nats_client_sender.publish(
            subject=subject, payload=self._dict_to_bytes(message), reply=reply
        )

    def reconnect(self):
        if (
            self.auto_reconnect
        ):  # reconnects nats_client for next call, if it was disconnected earlier
            try:
                self.nats_client_sender.ping()
            except Exception:
                self.nats_client_sender.reconnect()

    def request(self, subject: str, message: dict) -> dict:
        self.reconnect()

        return self._bytes_to_dict(
            self.nats_client_sender.request(
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
        self._subscribed_subjects.append(subject)
        return self.nats_client_listener.subscribe(
            subject=subject,
            callback=callback,
            queue=queue,
            max_messages=max_messages,
        )

    def wait(self, count: int) -> None:
        if self.nats_client_listener_thread is not None:
            raise TestClientError(
                "You can't use client.wait, "
                "if you don't have any @client.listen functions "
                "or you don't use do_always_listen=False!"
            )
        self.nats_client_listener.wait(count=count)

    def listen(self, subject: str):
        def decorator(func):
            assert isinstance(subject, str), "Subject must be only in str format"

            def wrapper(incoming_message):
                assert isinstance(incoming_message, NATSMessage)
                incoming_message_data = self._bytes_to_dict(incoming_message.payload)

                msg = Msg(
                    subject=incoming_message.subject,
                    data=incoming_message_data,
                    reply=incoming_message.reply,
                    sid=incoming_message.sid,
                )
                wrapper_response = func(msg)
                if wrapper_response is not None and incoming_message.reply != "":
                    self.nats_client_listener.publish(
                        subject=incoming_message.reply,
                        payload=self._dict_to_bytes(wrapper_response),
                    )

            self.subscribe(subject, wrapper)

            return wrapper

        return decorator
