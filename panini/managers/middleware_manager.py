import asyncio
from typing import Callable, Type

from panini.middleware import Middleware


class MiddlewareManager:

    def __init__(self):
        self._middlewares = {
            "send_publish_middleware": [],
            "listen_publish_middleware": [],
            "send_request_middleware": [],
            "listen_request_middleware": [],
        }

    @property
    def middlewares(self):
        return self._middlewares

    @middlewares.setter
    def middlewares(self, value: dict):
        self._middlewares = value

    def add_middleware(self, middleware_cls: Type[Middleware], *args, **kwargs):
        assert issubclass(middleware_cls, Middleware), \
            "Each custom middleware class must be a subclass of Middleware"

        high_priority_functions = (
            "send_publish",
            "listen_publish",
            "send_request",
            "listen_request",
        )

        global_functions = (
            "send_any",
            "listen_any"
        )

        # check, that at least one function is implemented
        assert any(
            function in middleware_cls.__dict__
            for function in high_priority_functions + global_functions
        ), f"At least one of the following functions must be implemented: {high_priority_functions + global_functions}"

        middleware_obj = middleware_cls(*args, **kwargs)
        for function_name in high_priority_functions:
            if function_name in middleware_cls.__dict__:
                self._middlewares[f"{function_name}_middleware"].append(
                    getattr(middleware_obj, function_name)
                )

        if "send_any" in middleware_cls.__dict__:
            if "send_publish" not in middleware_cls.__dict__:
                self._middlewares["send_publish_middleware"].append(
                    middleware_obj.send_any
                )

            if "send_request" not in middleware_cls.__dict__:
                self._middlewares["send_request_middleware"].append(
                    middleware_obj.send_any
                )

        if "listen_any" in middleware_cls.__dict__:
            if "listen_publish" not in middleware_cls.__dict__:
                self._middlewares["listen_publish_middleware"].append(
                    middleware_obj.listen_any
                )

            if "listen_request" not in middleware_cls.__dict__:
                self._middlewares["listen_request_middleware"].append(
                    middleware_obj.listen_any
                )

    def wrap_function_by_middleware(self, function_type: str) -> Callable:
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

                async def async_next_wrapper(subject: str, message, *args, **kwargs):
                    return await single_middleware(
                        subject, message, func, *args, **kwargs
                    )

                if asyncio.iscoroutinefunction(single_middleware):
                    return async_next_wrapper
                else:
                    return next_wrapper

            def wrap_function_by_listen_middleware(
                    func: Callable, single_middleware
            ) -> Callable:
                def next_wrapper(msg):
                    return single_middleware(msg, func)

                async def async_next_wrapper(msg):
                    return await single_middleware(msg, func)

                if asyncio.iscoroutinefunction(single_middleware):
                    return async_next_wrapper
                else:
                    return next_wrapper

            def build_middleware_wrapper(
                    func: Callable, middleware_key: str, wrapper: Callable
            ) -> Callable:
                for middleware in self._middlewares[middleware_key]:
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
                        len(self._middlewares["listen_publish_middleware"]) == 0
                        and len(self._middlewares["listen_request_middleware"])
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

                async def async_listen_wrapper(msg) -> Callable:
                    if msg.reply == "":
                        return await function_listen_publish(msg)
                    else:
                        return await function_listen_request(msg)

                if asyncio.iscoroutinefunction(function):
                    return async_listen_wrapper
                else:
                    return listen_wrapper

        return decorator
