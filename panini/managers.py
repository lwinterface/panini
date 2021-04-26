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
        self,
        subject: list or str,
        validator: type = None,
        dynamic_subscription=False,
        data_type="json.loads",
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
                except InitializingIntervalTaskError:
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
                except InitializingIntervalTaskError:
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

    @staticmethod
    def add_middleware(middleware_cls: Type[Middleware], *args, **kwargs):
        assert issubclass(
            middleware_cls, Middleware
        ), "Each custom middleware class must be a subclass of Middleware"
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
                _MiddlewareManager.MIDDLEWARE[f"{function_name}_middleware"].append(
                    getattr(middleware_obj, function_name)
                )

        if "send_any" in middleware_cls.__dict__:
            if "send_publish" not in middleware_cls.__dict__:
                _MiddlewareManager.MIDDLEWARE["send_publish_middleware"].append(
                    middleware_obj.send_any
                )

            if "send_request" not in middleware_cls.__dict__:
                _MiddlewareManager.MIDDLEWARE["send_request_middleware"].append(
                    middleware_obj.send_any
                )

        if "listen_any" in middleware_cls.__dict__:
            if "listen_publish" not in middleware_cls.__dict__:
                _MiddlewareManager.MIDDLEWARE["listen_publish_middleware"].append(
                    middleware_obj.listen_any
                )

            if "listen_request" not in middleware_cls.__dict__:
                _MiddlewareManager.MIDDLEWARE["listen_request_middleware"].append(
                    middleware_obj.listen_any
                )

    @staticmethod
    def _wrap_function_by_middleware(function_type: str) -> Callable:
        """
        function: Callable - function to wrap
        function_type: str - one of the ["listen", "publish", "request"]
        """
        assert function_type in (
            "listen",
            "publish",
            "request",
        ), "function type must be in (`listen`, `publish`, `request`)"

        def decorator(function: Callable):
            def wrap_function_by_send_middleware(
                func: Callable, single_middleware
            ) -> Callable:
                def next_wrapper(subject: str, message, *args, **kwargs):
                    return single_middleware(subject, message, func, *args, **kwargs)

                async def aio_next_wrapper(subject: str, message, *args, **kwargs):
                    return await single_middleware(
                        subject, message, func, *args, **kwargs
                    )

                if asyncio.iscoroutinefunction(single_middleware):
                    return aio_next_wrapper
                else:
                    return next_wrapper

            def wrap_function_by_listen_middleware(
                func: Callable, single_middleware
            ) -> Callable:
                def next_wrapper(msg):
                    return single_middleware(msg, func)

                async def aio_next_wrapper(msg):
                    return await single_middleware(msg, func)

                if asyncio.iscoroutinefunction(single_middleware):
                    return aio_next_wrapper
                else:
                    return next_wrapper

            def build_middleware_wrapper(
                func: Callable, middleware_key: str, wrapper: Callable
            ) -> Callable:
                for middleware in _MiddlewareManager.MIDDLEWARE[middleware_key]:
                    func = wrapper(func, middleware)
                return func

            if function_type == "publish":
                return build_middleware_wrapper(
                    function,
                    "send_publish_middleware",
                    wrap_function_by_send_middleware,
                )

            elif function_type == "request":
                return build_middleware_wrapper(
                    function,
                    "send_request_middleware",
                    wrap_function_by_send_middleware,
                )

            else:
                if (
                    len(_MiddlewareManager.MIDDLEWARE["listen_publish_middleware"]) == 0
                    and len(_MiddlewareManager.MIDDLEWARE["listen_request_middleware"])
                    == 0
                ):
                    return function

                function_listen_publish = build_middleware_wrapper(
                    function,
                    "listen_publish_middleware",
                    wrap_function_by_listen_middleware,
                )
                function_listen_request = build_middleware_wrapper(
                    function,
                    "listen_request_middleware",
                    wrap_function_by_listen_middleware,
                )

                def listen_wrapper(msg) -> Callable:
                    if msg.reply == "":
                        return function_listen_publish(msg)
                    else:
                        return function_listen_request(msg)

                async def aio_listen_wrapper(msg) -> Callable:
                    if msg.reply == "":
                        return await function_listen_publish(msg)
                    else:
                        return await function_listen_request(msg)

                if asyncio.iscoroutinefunction(function):
                    return aio_listen_wrapper
                else:
                    return listen_wrapper

        return decorator
