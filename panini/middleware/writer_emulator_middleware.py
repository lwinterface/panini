import json
import os
import threading
import time
import collections
from datetime import datetime
from typing import Any

from panini import middleware
from panini.app import get_app


class _Writer(threading.Thread):
    def __init__(self, filename: str):
        threading.Thread.__init__(self)

        self._array = collections.deque()
        self._lock = threading.Lock()

        self._filename = filename

    def add(self, event: dict):
        with self._lock:
            self._array.append(event)

    def run(self):

        """
        This is a main method of _Writer.
        It checks the array in order to write it to the file with events

        It keeps the file opened if there are any messages, to do not spend time for reopen every time

        Also, it has gradually increasing sleep timer

        """

        file = None
        min_sleep_time = 0.1
        max_sleep_time = 1
        sleep_time = min_sleep_time
        while True:
            try:
                if len(self._array) == 0:
                    # close file only when array is empty
                    if file:
                        file.close()
                        file = None

                    # gradually increase sleep time, in order to handle appeared massages faster
                    time.sleep(sleep_time)
                    sleep_time = min(max_sleep_time, sleep_time * 2)
                else:
                    if not file:
                        file = open(self._filename, "a")

                    line = self._array.popleft()
                    file.write(json.dumps(line) + os.linesep)
                    sleep_time = min_sleep_time
            except Exception as ex:
                print(f"exception: {ex}")


class WriterEmulatorMiddleware(middleware.Middleware):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

        app = get_app()
        print("Emulator is experimental feature!")
        folder = kwargs.get("folder")
        if not os.path.isdir(folder):
            os.makedirs(folder)

        filename = f"{folder}/events.{app.service_name}.{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.jsonl"
        self._prefix = kwargs.get("prefix", "emulator")
        self._writer = _Writer(filename)
        self._writer.start()

    async def send_publish(self, subject: str, message: Any, publish_func, **kwargs):

        self._writer.add(
            {
                "event_type": "send_publish",
                "subject": subject,
                "message": message,
                "timestamp": time.time(),
            }
        )

        await publish_func(subject, message, **kwargs)

    async def send_request(self, subject: str, message: Any, request_func, **kwargs):
        response = await request_func(subject, message, **kwargs)

        self._writer.add(
            {
                "event_type": "send_request",
                "subject": subject,
                "message": message,
                "response": response,
                "timestamp": time.time(),
            }
        )

        return response

    async def listen_publish(self, msg, callback):

        self._writer.add(
            {
                "event_type": "listen_publish",
                "subject": msg.subject,
                "message": msg.data,
                "context": msg.context,
                "timestamp": time.time(),
            }
        )

        await callback(msg)

    async def listen_request(self, msg, callback):

        response = await callback(msg)

        self._writer.add(
            {
                "event_type": "listen_request",
                "subject": msg.subject,
                "message": msg.data,
                "context": msg.context,
                "response": response,
                "timestamp": time.time(),
            }
        )

        return response
