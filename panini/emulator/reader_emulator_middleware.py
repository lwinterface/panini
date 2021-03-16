from panini import middleware
from panini.app import get_app
import copy

class ReaderEmulatorMiddleware(middleware.Middleware):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

        self._prefix = kwargs.get("prefix", "emulator")

        app = get_app()
        assert app is not None

        subjects = copy.copy(list(app.SUBSCRIPTIONS.keys()))
        for subject in subjects:
            subject_with_prefix = self._prefix + "." + subject
            app.SUBSCRIPTIONS[subject_with_prefix] = app.SUBSCRIPTIONS.pop(subject)

    async def send_publish(self, subject: str, message, publish_func, **kwargs):
        # add prefix
        # subject = self._prefix + "." + subject

        await publish_func(subject, message, **kwargs)

    async def send_request(self, subject: str, message, request_func, **kwargs):
        # add prefix
        # subject = self._prefix + "." + subject

        response = await request_func(subject, message, **kwargs)
        return response

    async def listen_publish(self, msg, callback):
        # remove prefix
        msg.subject = msg.subject[len(self._prefix) + 1:]

        await callback(msg)

    async def listen_request(self, msg, callback):
        # remove prefix
        msg.subject = msg.subject[len(self._prefix) + 1:]

        response = await callback(msg)
        return response
