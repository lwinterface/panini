from panini.middleware import Middleware
from panini.utils.logger import get_logger


class DebugMiddleware(Middleware):
    def __init__(
        self,
        logger=None,
        logger_name="panini",
        log_level="debug",
        use_send_any=True,
        use_listen_any=True,
    ):
        self.logger = logger if logger is not None else get_logger(logger_name)
        self.log_level = log_level.lower()
        self.use_send_any = use_send_any
        self.use_listen_any = use_listen_any

    def _log(self, *args, **kwargs):
        return getattr(self.logger, self.log_level)(*args, **kwargs)

    async def send_any(self, subject: str, message, send_func, *args, **kwargs):
        if not self.use_send_any:
            return await send_func(subject, message, *args, **kwargs)

        self._log(f"Sent to {subject} message {message}")
        response = await send_func(subject, message, *args, **kwargs)
        if response is not None:
            self._log(f"Received response: {response}")

        return response

    async def listen_any(self, msg, callback):
        if not self.use_listen_any:
            return await callback(msg)

        self._log(f"Listen to {msg.subject} with payload {msg.data}")
        response = await callback(msg)
        if response is not None:
            self._log(f"Answered to it: {response}")

        return response
