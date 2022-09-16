import asyncio
from dataclasses import dataclass
from typing import Optional, Callable

from nats.aio.msg import Msg
from nats.js import api

from panini import exceptions
from panini.exceptions import NotReadyError, ValidationError


@dataclass
class Listen:
    callback: Callable
    subject: str
    data_type: str | type = "json"
    queue: str = ""

@dataclass
class JsListen(Listen):
    durable: Optional[str] = None
    stream: Optional[str] = None
    config: Optional[api.ConsumerConfig] = None
    manual_ack: Optional[bool] = False
    ordered_consumer: Optional[bool] = False
    idle_heartbeat: Optional[float] = None
    flow_control: Optional[bool] = False


class EventManager:
    """
    Collect all functions from each module wrapped by @app.subscription or @EventManager.subscribe
    """

    def __init__(self):
        self._subscriptions = {}
        self._js_subscriptions = {}

    @property
    def subscriptions(self):
        return self._subscriptions

    @property
    def js_subscriptions(self):
        return self._js_subscriptions

    def listen(
        self,
        subject: list | str,
        data_type="json",
        validator: type = None,
        validation_error_cb: Callable[[Msg, ValidationError], None] = None,
        **kwargs
    ):
        def wrapper(function):
            function = self.wrap_function_by_validator(function, validator, validation_error_cb)
            if isinstance(subject, list):
                for s in subject:
                    self._create_subscription_if_missing(t)
                    listen_obj = Listen(
                        callback=function,
                        subject=s,
                        data_type=data_type,
                        **kwargs
                    )
                    self._subscriptions[s].append(listen_obj)
            else:
                self._create_subscription_if_missing(subject)
                listen_obj = Listen(
                    callback=function,
                    subject=subject,
                    data_type=data_type,
                    **kwargs
                )
                self._subscriptions[subject].append(listen_obj)
            return function
        return wrapper

    def js_listen(
        self,
        subject: list | str,
        data_type: type | str = "json",
        validator: type = None,
        validation_error_cb: Callable[[Msg, ValidationError], None] = None,
        **kwargs,
    ):
        """
        "PUSH" listen/subscribe
        """
        def wrapper(function):
            function = self.wrap_function_by_validator(function, validator, validation_error_cb)
            self._create_subscription_if_missing(subject, js=True)
            js_listen_obj = JsListen(
                callback=function,
                subject=subject,
                data_type=data_type,
                **kwargs
            )
            self._js_subscriptions[subject].append(js_listen_obj)
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

    def _create_subscription_if_missing(self, subscription, js=False):
        if js:
            if subscription not in self._js_subscriptions:
                self._js_subscriptions[subscription] = []
        else:
            if subscription not in self._subscriptions:
                self._subscriptions[subscription] = []
