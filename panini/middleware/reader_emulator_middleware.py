import uuid

from panini.app import get_app
import copy

from panini.emulator_client import EmulatorClient
from panini.middleware import Middleware
from panini.nats_client import Msg
from panini.utils.helper import start_thread


class ReaderEmulatorMiddleware(Middleware):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

        self._prefix = kwargs.get("prefix", str(uuid.uuid4()))

        app = get_app()
        assert app is not None
        print("Emulator is experimental feature!")
        subjects = copy.copy(list(app.SUBSCRIPTIONS.keys()))
        for subject in subjects:
            subject_with_prefix = self._prefix + "." + subject
            app.SUBSCRIPTIONS[subject_with_prefix] = app.SUBSCRIPTIONS.pop(subject)

        self._run_emulator = kwargs.get("run_emulator", True)

        if self._run_emulator:
            emulator = EmulatorClient(
                prefix=self._prefix,
                filepath=kwargs.get("filename"),
                emulate_timeout=kwargs.get("emulate_timeout", True),
                compare_output=kwargs.get("compare_output", False),
                app_name=app.service_name,
            )
            start_thread(emulator.start)
            emulator.wait_for_readiness()

    async def listen_any(self, message: Msg, callback):
        message.subject = message.subject[len(self._prefix) + 1 :]
        response = await callback(message)
        return response

    async def send_any(self, subject: str, message, send_func, *args, **kwargs):
        subject = self._prefix + "." + subject
        response = await send_func(subject, message, *args, **kwargs)
        return response
