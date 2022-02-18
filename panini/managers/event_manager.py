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
        data_type="json",
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
        return wrapper

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
            res = validate_message(msg)
            return function(msg, validation_report=res)

        async def wrapper_async(msg):
            res = validate_message(msg)
            return await function(msg, validation_report=res)

        if asyncio.iscoroutinefunction(function):
            return wrapper_async
        else:
            return wrapper

    def _check_subscription(self, subscription):
        if subscription not in self._subscriptions:
            self._subscriptions[subscription] = []
