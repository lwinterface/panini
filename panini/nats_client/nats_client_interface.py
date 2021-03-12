from abc import ABC, abstractmethod

from ..utils.logger import get_logger


class Msg:
    """
    Alternative implementation of the class with "context" field
    """

    __slots__ = ("subject", "reply", "data", "sid", "context")

    def __init__(self, subject="", reply="", data=b"", sid=0, context={}):
        self.subject = subject
        self.reply = reply
        self.data = data
        self.sid = sid
        self.context = context

    def __repr__(self):
        return "<{}: subject='{}' reply='{}' context='{}...'>".format(
            self.__class__.__name__,
            self.subject,
            self.reply,
            self.context,
        )


class NATSClientInterface(ABC):
    def __init__(
        self,
        client_id: str,
        host: str,
        port: int or str,
        listen_subjects_callbacks: dict,
        allow_reconnect: bool or None,
        max_reconnect_attempts: int = 60,
        reconnecting_time_wait: int = 2,
        publish_subjects=[],
        auth: dict = {},
        queue="",
        client_strategy="asyncio",  # in_current_process' or in_separate_processes'
        redis_host="127.0.0.1",
        redis_port="6379",
        pending_bytes_limit=65536 * 1024 * 10,
        num_of_queues=1,
    ):
        """
        :param client_id: instance identifier for NATS, str
        :param port: default '4333'
        :param publish_subjects: for example public.binance.order_book.BTC_USD
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        :return: {'success': True} if success otherwise  {'success': False, 'error': 'error description'}
        """
        self.log = get_logger("panini")
        self.connected = False
        self.client_id = client_id
        self.host = host
        self.port = port
        self.queue = queue
        self.auth = auth
        self.listen_subjects_callbacks = listen_subjects_callbacks
        self.publish_subjects = publish_subjects
        self.allow_reconnect = allow_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnecting_time_wait = reconnecting_time_wait
        self.client_strategy = client_strategy
        self.pending_bytes_limit = pending_bytes_limit
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.num_of_queues = num_of_queues

    @abstractmethod
    def check_connection(self):
        pass

    @abstractmethod
    def subscribe_new_subject(self, subject: str, callback):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def publish_sync(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        pass

    @abstractmethod
    def request_sync(
        self,
        subject: str,
        message,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
    ):
        pass

    @abstractmethod
    async def publish(
        self,
        subject: str,
        message,
        reply_to: str = None,
        force: bool = False,
        data_type: type or str = "json.dumps",
    ):
        pass

    @abstractmethod
    async def request(
        self,
        subject: str,
        message,
        timeout: int = 10,
        data_type: type or str = "json.dumps",
    ):
        pass

    @abstractmethod
    def request_from_another_thread_sync(
        self,
        subject: str,
        message,
        timeout: int = 10,
    ):
        pass

    @abstractmethod
    async def request_from_another_thread(
        self,
        subject: str,
        message,
        timeout: int = 10,
    ):
        pass
