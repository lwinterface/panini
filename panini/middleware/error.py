import typing
import asyncio

from . import Middleware


class ErrorMiddleware(Middleware):
    def __init__(self, error: Exception, callback: typing.Callable, *args, **kwargs):
        """
        :param error: Exception to catch
        :param callback: callback, that will handle an error if raises
                         callback must accept error, subject, message, msg parameters
                         in order to provide full data about the error case
        """
        super().__init__(*args, **kwargs)
        self.error = error
        self.callback = callback

    async def send_any(self, subject: str, message, send_func, *args, **kwargs):
        try:
            response = await send_func(subject, message, *args, **kwargs)
            return response
        except self.error as e:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(e, subject=subject, message=message)
            else:
                self.callback(e, subject=subject, message=message)

    async def listen_any(self, msg, callback):
        try:
            response = await callback(msg)
            return response
        except self.error as e:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(e, msg=msg)
            else:
                self.callback(e, msg=msg)
