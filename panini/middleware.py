class Middleware:
    def __init__(self, *args, **kwargs):
        pass

    async def send_publish(self, subject: str, message, publish_func, *args, **kwargs):
        """
        :param subject: str
        :param message: any of supported types
        :param publish_func: Callable for publish
        :return: None
        """
        pass

    async def listen_publish(self, msg, callback):
        """
        :param msg: Msg
        :param callback: Callable, that will be called on receive message
        :return: None
        """
        pass

    async def send_request(self, subject: str, message, request_func, *args, **kwargs):
        """
        :param subject: str
        :param message: any of supported types
        :param request_func: Callable for request
        :return: any of supported types
        """
        pass

    async def listen_request(self, msg, callback):
        """
        :param msg: Msg
        :param callback: Callable, that will be called on receive message
        :return: any of supported types
        """
        pass

    async def send_any(self, subject: str, message, send_func, *args, **kwargs):
        """
        :param subject: str
        :param message: any of supported types
        :param send_func: Callable for send
        :return: None or any of supported types
        """

    async def listen_any(self, msg, callback):
        """
        :param msg: Msg
        :param callback: Callable, that will be called on receive message
        :return: None or any of supported types
        """
