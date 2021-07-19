import asyncio
import os
import shutil
import json
import random
import time
import typing
from urllib.parse import urljoin

import requests
import websocket
from nats.aio.client import Client as NATS

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


def is_subject_matches_pattern(subject: str, pattern: str) -> bool:
    subject_parts = subject.split(".")
    pattern_parts = pattern.split(".")
    if ">" in pattern:
        assert pattern[-1] == ">", "> must can be only the last element of subject!"
        gt_position = pattern_parts.index(">")
        return is_subject_matches_pattern(
            ".".join(subject_parts[:gt_position]),
            ".".join(pattern_parts[:gt_position]),
        )

    if ">" in subject_parts:
        return False

    if len(subject_parts) != len(pattern_parts):
        return False

    for index, part in enumerate(pattern_parts):
        if part == "*":
            pass
        elif part != subject_parts[index]:
            return False

    return True


class AsyncTestClient:
    __test__ = False

    def __init__(
        self,
        run_panini: typing.Callable = None,
        run_panini_args: list = None,
        run_panini_kwargs: dict = None,
        run_panini_timeout: float = 5,
        panini_service_name: str = "*",
        panini_client_id: str = "*",
        logger_files_path: str = "test_logs",
        use_web_server: bool = False,
        use_web_socket: bool = False,
        base_web_server_url: str = "http://127.0.0.1:8080",
        nats_host: str = "127.0.0.1",
        nats_port: int = 4222,
        name: str = "__".join(
            [
                "test_client",
                str(random.randint(1, 10000000)),
                str(random.randint(1, 10000000)),
            ]
        ),
        listen_subjects_callbacks: dict = None,
    ):
        self.run_panini = run_panini
        self.run_panini_args = run_panini_args or []
        self.run_panini_kwargs = run_panini_kwargs or {}
        self.run_panini_timeout = run_panini_timeout
        self.listen_subjects_callbacks = listen_subjects_callbacks or {}
        self.panini_service_name = panini_service_name
        self.panini_client_id = panini_client_id
        self.logger_files_path = logger_files_path
        self.base_web_server_url = base_web_server_url
        self.use_web_server = use_web_server
        self.use_web_socket = use_web_socket
        self.name = name
        self.nats_client = NATS()
        self.nats_client.msg_class = Msg
        self.nats_host = nats_host
        self.nats_port = nats_port
        self._listen_subjects_count_calls = {}

        if use_web_server:
            self.http_session = HTTPSessionTestClient(base_url=base_web_server_url)

        if use_web_socket:
            self.websocket_session = websocket.WebSocket()

        self.panini_process = None

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

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            run_panini(*run_panini_args, **run_panini_kwargs)
        except Exception as e:
            test_logger.exception(f"Run panini error: {e}")

    async def start(self, is_daemon: bool = True, use_error_middleware=True):
        await self.nats_client.connect(
            f"{self.nats_host}:{self.nats_port}", name=self.name
        )
        for subject, callback in self.listen_subjects_callbacks.items():
            await self.nats_client.subscribe(subject, cb=callback)

        if self.run_panini is not None:

            panini_started_future = asyncio.Future()

            def panini_started(msg):
                panini_started_future.set_result(msg)

            sid = await self.nats_client.subscribe(
                f"panini_events.{self.panini_service_name}.{self.panini_client_id}.started",
                cb=panini_started,
            )
            await self.nats_client.auto_unsubscribe(sid, 1)

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
                await asyncio.wait_for(panini_started_future, self.run_panini_timeout)
            except Exception:
                raise TestClientError(
                    "TestClient was waiting panini to start, but panini does not started"
                )

            if self.use_web_server:
                pass  # TODO: understand, why don't we need to wait for web_server

        return self

    async def stop(self):
        await self.nats_client.drain()
        await self.nats_client.close()

        if self.panini_process is not None:
            self.panini_process.kill()

        if hasattr(self, "http_session"):
            self.http_session.close()

        if hasattr(self, "websocket_session"):
            self.websocket_session.close()

    async def publish(self, subject: str, message: dict, reply_to: str = "") -> None:
        message = self._dict_to_bytes(message)
        if reply_to is not None:
            await self.nats_client.publish_request(subject, reply_to, message)
        else:
            await self.nats_client.publish(subject, message)

    async def request(self, subject: str, message: dict, timeout: int = 1) -> dict:
        response = await self.nats_client.request(
            subject=subject, payload=self._dict_to_bytes(message), timeout=timeout
        )
        return self._bytes_to_dict(response.data)

    async def subscribe(
        self,
        subject: str,
        callback: typing.Callable,
        queue: str = "",
        max_messages: typing.Optional[int] = 0,
    ):
        return await self.nats_client.subscribe(
            subject=subject,
            cb=callback,
            queue=queue,
            max_msgs=max_messages,
        )

    def total_count_subject_calls(self, count_calls: dict = None):
        if count_calls is None:
            count_calls = self._listen_subjects_count_calls
        return sum(count_calls.values())

    def count_subject_calls(self, subject: str, count_calls: dict = None):
        """Count calls for specific subject (this subject is used as pattern for subject - supports * and >)"""
        if count_calls is None:
            count_calls = self._listen_subjects_count_calls
        res_count = 0
        for listen_subject, count in count_calls.items():
            if is_subject_matches_pattern(listen_subject, subject):
                res_count += count

        return res_count

    def clear_listen_subjects_count_calls(self):
        """Clean up all counts for subject called in AsyncTestClient"""
        self._listen_subjects_count_calls = {}

    async def wait(
        self,
        count: int = 0,
        timeout: float = 1,
        subject: str = None,
        subjects: dict = None,
    ) -> None:
        """
        Waits for test client subjects to be triggered & handled.
        count: how much calls wait
        timeout: maximum seconds to wait
        subject: which subject to wait
        subjects: dict of subjects, with subject as key and count_to_wait as value
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if subject is not None:
                if self.count_subject_calls(subject) >= count:
                    return
            elif subjects is not None:
                if all(
                    [
                        self.count_subject_calls(subj) >= count_call
                        for subj, count_call in subjects.items()
                    ]
                ):
                    return
            elif self.total_count_subject_calls() >= count:
                return
            await asyncio.sleep(0)

        # wait was not successful
        if subject is not None:
            report_msg = f"subject: {subject} was called {self.count_subject_calls(subject)} times"
        elif subjects is not None:
            subjects_calls = {subj: self.count_subject_calls(subj) for subj in subjects}
            report_msg = f"subjects were called {subjects_calls} times"
        else:
            report_msg = f"total_count_subject_calls={self.total_count_subject_calls()}"
        raise asyncio.TimeoutError(
            f"Timeout while waiting for listen_subjects to be called! Params - count: {count}, timeout: {timeout}, subject: {subject}, subjects: {subjects}. Actual state: {report_msg}"
        )

    def listen(self, subject: str):
        def decorator(func):
            assert isinstance(subject, str), "Subject must be only in str format"

            async def wrapper(incoming_message):
                assert isinstance(
                    incoming_message, Msg
                ), "Incoming message must be instance of Msg!"
                incoming_message_data = self._bytes_to_dict(incoming_message.data)

                msg = Msg(
                    subject=incoming_message.subject,
                    data=incoming_message_data,
                    reply=incoming_message.reply,
                    sid=incoming_message.sid,
                )
                if asyncio.iscoroutinefunction(func):
                    wrapper_response = await func(msg)
                else:
                    wrapper_response = func(msg)
                if wrapper_response is not None and incoming_message.reply != "":
                    await self.nats_client.publish(
                        subject=incoming_message.reply,
                        payload=self._dict_to_bytes(wrapper_response),
                    )

                self._listen_subjects_count_calls[msg.subject] = (
                    self._listen_subjects_count_calls.get(msg.subject, 0) + 1
                )

            self.listen_subjects_callbacks[subject] = wrapper

            return wrapper

        return decorator
