import time
import asyncio
from . import exceptions
from typing import Callable, Type
from .exceptions import (
    ValidationError,
    InitializingIntervalTaskError,
    NotReadyError,
    BaseError,
)
from .middleware import Middleware


class _EventManager:
    """
    Collect all functions from each module wrapped by @app.subscription or @EventManager.subscribe
    """

    SUBSCRIPTIONS = {}

    def listen(
        self, subject: list or str, validator: type = None, dynamic_subscription=False
    ):
        def wrapper(function):
            function = _EventManager.wrap_function_by_validator(function, validator)
            if type(subject) is list:
                for t in subject:
                    _EventManager._check_subscription(t)
                    _EventManager.SUBSCRIPTIONS[t].append(function)
            else:
                _EventManager._check_subscription(subject)
                _EventManager.SUBSCRIPTIONS[subject].append(function)
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
        self.subscribe_new_subject(subject, function)

    @staticmethod
    def wrap_function_by_validator(function, validator):
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

    @staticmethod
    def _check_subscription(subscription):
        if subscription not in _EventManager.SUBSCRIPTIONS:
            _EventManager.SUBSCRIPTIONS[subscription] = []


class _TaskManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """

    TASKS = []

    @staticmethod
    def task(**kwargs):
        def wrapper(task):
            _TaskManager._check_task(task)
            _TaskManager.TASKS.append(task)
            return task

        return wrapper

    @staticmethod
    def _check_task(task):
        # TODO
        pass


class _IntervalTaskManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """

    INTERVAL_TASKS = {}

    @staticmethod
    def timer_task(interval: float or int):
        def wrapper(interval_task: Callable):
            _IntervalTaskManager._check_timer_task(interval, interval_task)
            if asyncio.iscoroutinefunction(interval_task):
                interval_task = _IntervalTaskManager.wrap_coro_by_interval(
                    interval, interval_task
                )
            else:
                interval_task = _IntervalTaskManager.wrap_function_by_interval(
                    interval, interval_task
                )
            if interval not in _IntervalTaskManager.INTERVAL_TASKS:
                _IntervalTaskManager.INTERVAL_TASKS[interval] = []
            _IntervalTaskManager.INTERVAL_TASKS[interval].append(interval_task)
            return interval_task

        return wrapper

    @staticmethod
    def wrap_coro_by_interval(interval, interval_task):
        async def wrapper(**kwargs):
            while True:
                try:
                    await interval_task(**kwargs)
                    await asyncio.sleep(interval)
                except InitializingIntervalTaskError as e:
                    # TODO: warning log
                    pass

        return wrapper

    @staticmethod
    def wrap_function_by_interval(interval, interval_task):
        def wrapper(**kwargs):
            while True:
                try:
                    interval_task(**kwargs)
                    time.sleep(interval)
                except InitializingIntervalTaskError as e:
                    # TODO: warning log
                    pass

        return wrapper

    @staticmethod
    def _check_timer_task(interval, interval_task):
        # TODO
        pass


class _MiddlewareManager:
    MIDDLEWARE = {
        "send_publish_middleware": [],
        "listen_publish_middleware": [],
        "send_request_middleware": [],
        "listen_request_middleware": [],
    }

    def add_middleware(self, middleware_cls: Type[Middleware], *args, **kwargs):
        assert issubclass(middleware_cls, Middleware), "Each custom middleware class must be a subclass of Middleware"
        high_priority_functions = (
            "send_publish",
            "listen_publish",
            "send_request",
            "listen_request",
        )
        global_functions = ("send_any", "listen_any")

        # check, that at least one function is implemented
        assert any(
            function in middleware_cls.__dict__
            for function in high_priority_functions + global_functions
        ), f"At least one of the following functions must be implemented: {high_priority_functions + global_functions}"

        middleware_obj = middleware_cls(*args, **kwargs)
        for function_name in high_priority_functions:
            if function_name in middleware_cls.__dict__:
                self.MIDDLEWARE[f"{function_name}_middleware"].append(
                    getattr(middleware_obj, function_name)
                )

        if "send_any" in middleware_cls.__dict__:
            if "send_publish" not in middleware_cls.__dict__:
                self.MIDDLEWARE[f"send_publish_middleware"].append(
                    middleware_obj.send_any
                )

            if "send_request" not in middleware_cls.__dict__:
                self.MIDDLEWARE[f"send_request_middleware"].append(
                    middleware_obj.send_any
                )

        if "listen_any" in middleware_cls.__dict__:
            if "listen_publish" not in middleware_cls.__dict__:
                self.MIDDLEWARE[f"listen_publish_middleware"].append(
                    middleware_obj.listen_any
                )

            if "listen_request" not in middleware_cls.__dict__:
                self.MIDDLEWARE[f"listen_request_middleware"].append(
                    middleware_obj.listen_any
                )

    @staticmethod
    def wrap_function_by_middleware():
        # TODO: implement wrapping callbacks and functions
        pass
