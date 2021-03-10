import typing
import asyncio

from . import Middleware


class ErrorMiddleware(Middleware):
    def __init__(self, error: Exception, callback: typing.Callable):
        self.error = error
        self.callback = callback

    async def send_any(self, subject: str, message, send_func, *args, **kwargs):
        try:
            response = await send_func(subject, message, *args, **kwargs)
            return response
        except self.error as e:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(e)
            else:
                self.callback(e)

    async def listen_any(self, msg, callback):
        try:
            response = await callback(msg)
            return response
        except self.error as e:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(e)
            else:
                self.callback(e)
