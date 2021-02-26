import os
import time
import datetime

from nats.aio.errors import ErrTimeout

from ..utils.redis_queue import RedisQueue
from ..utils.logger import get_logger


class RedisResponse(RedisQueue):
    def __init__(
        self,
        name: str,
        namespace: str = "response",
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        waiting_between_check: float = 0.001,
    ):
        self.log = get_logger("RedisResponse")
        if "SERVICE_NAME" in os.environ:
            if "_sender_client" in os.environ["SERVICE_NAME"]:
                service_name = os.environ["SERVICE_NAME"].replace("_sender_client", "")
            else:
                service_name = os.environ["SERVICE_NAME"]
            self._name = "_".join([service_name, name])
        else:
            self._name = "_".join(["Unknown", name])
        super().__init__(name, namespace, host, port, db)
        self.waiting_between_check = waiting_between_check

    def return_response_when_appeared(self, subject=None, timeout=30):
        started = datetime.datetime.now().timestamp()
        while datetime.datetime.now().timestamp() - started < timeout:
            try:
                if self.empty():
                    time.sleep(self.waiting_between_check)
                    continue
                return self.get()
            except Exception as e:
                self.log.exception("RedisResponse error: ", str(e))
        msg = "Nats client timeout"
        self.log.error(
            f"Waiting for response from redis ERROR: {msg}, subject: {subject}"
        )
        raise ErrTimeout(msg)
