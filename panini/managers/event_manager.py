import asyncio

from panini import exceptions
from panini.exceptions import NotReadyError, ValidationError


class EventManager:
    """
    Collect all functions from each module wrapped by @app.subscription or @EventManager.subscribe
    """

    def __init__(self):
        self._subscriptions = {}

    @property
    def subscriptions(self):
        return self._subscriptions

    def listen(
        self,
        subject: list or str,
        validator: type = None,
        dynamic_subscription=False,
        data_type="json.loads",
    ):
        def wrapper(function):
            function = self.wrap_function_by_validator(function, validator)
            if type(subject) is list:
                for t in subject:
                    self._check_subscription(t)
                    self._subscriptions[t].append(function)
            else:
                self._check_subscription(subject)
                self._subscriptions[subject].append(function)
            function.data_type = data_type
            return function

        if dynamic_subscription:
            if type(subject) is list:
                for s in subject:
                    self._subscribe(s, wrapper)
            else:
                self._subscribe(subject, wrapper)
        return wrapper

    def _subscribe(self, subject, function):
        if not hasattr(self, "connector") or self.connector.check_connection is False:
            raise NotReadyError(
                "Something wrong. NATS client should be connected first"
            )
        self.subscribe_new_subject_sync(subject, function)

    def wrap_function_by_validator(self, function, validator):
        def validate_message(msg):
            try:
                if validator is not None:
                    validator.validated_message(msg.data)
            except exceptions.ValidationError as se:
                error = f"subject: {msg.subject} error: {str(se)}"
                return {"success": False, "error": error}
            except Exception as e:
                raise ValidationError(e)
            return msg

        def wrapper(msg):
            validate_message(msg)
            return function(msg)

        async def wrapper_async(msg):
            validate_message(msg)
            return await function(msg)

        if asyncio.iscoroutinefunction(function):
            return wrapper_async
        else:
            return wrapper

    def _check_subscription(self, subscription):
        if subscription not in self._subscriptions:
            self._subscriptions[subscription] = []
