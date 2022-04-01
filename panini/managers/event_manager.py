import asyncio
from types import FunctionType
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
        data_type="json",
        validator: type = None,
        validation_error_cb: FunctionType = None,
    ):
        def wrapper(function):
            function = self.wrap_function_by_validator(function, validator, validation_error_cb)
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

    def wrap_function_by_validator(self, function, validator, validation_error_cb):
        def validate_message(msg):
            try:
                if validator is not None:
                    validator.validated_message(msg.data)
            except exceptions.ValidationError as se:
                if validation_error_cb:
                    return validation_error_cb(msg, se)
                error = f"subject: {msg.subject} error: {str(se)}"
                return {"success": False, "error": error}
            except Exception as e:
                raise ValidationError(e)
            return True

        def wrapper(msg):
            validation_result = validate_message(msg)
            if not validation_result is True:
                return validation_result
            return function(msg)

        async def wrapper_async(msg):
            validation_result = validate_message(msg)
            if not validation_result is True:
                return validation_result
            return await function(msg)

        if asyncio.iscoroutinefunction(function):
            return wrapper_async
        else:
            return wrapper

    def _check_subscription(self, subscription):
        if subscription not in self._subscriptions:
            self._subscriptions[subscription] = []
