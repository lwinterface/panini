import traceback

from nats.aio.errors import ErrTimeout

from .error import ErrorMiddleware


class NATSTimeoutMiddleware(ErrorMiddleware):
    def __init__(self, app, subject, send_func_type: str = "request"):
        async def handle_nats_timeout_callback(error: Exception, **kwargs):
            error_msg = {"error": traceback.format_exc(), "error_msg": str(error)}
            error_msg.update(kwargs)
            if send_func_type == "request":
                response = await app.request(subject, error_msg)
                print("Response:", response)
            else:
                await app.publish(subject, error_msg)

        super().__init__(ErrTimeout, handle_nats_timeout_callback)

    async def send_any(self, subject: str, message, send_func, *args, **kwargs):
        return await super(NATSTimeoutMiddleware, self).send_any(
            subject, message, send_func, *args, **kwargs
        )

    async def listen_any(self, msg, callback):
        return await super(NATSTimeoutMiddleware, self).listen_any(msg, callback)
