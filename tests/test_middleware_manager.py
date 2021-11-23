import asyncio

import pytest

from panini import app as panini_app

from panini.middleware import Middleware


class FooMiddleware(Middleware):
    async def send_publish(self, subject: str, message, publish_func, **kwargs):
        """FooMiddleware send_publish"""  # docstring is important for testing
        pass  # implementation is not important for some of these tests

    async def listen_publish(self, msg, callback):
        """FooMiddleware listen_publish"""
        pass

    async def listen_request(self, msg, callback):
        """FooMiddleware listen_request"""
        pass


class BarMiddleware(Middleware):
    def send_request(self, subject: str, message, request_func, **kwargs):
        """BarMiddleware send_request"""
        pass

    def listen_publish(self, msg, callback):
        """BarMiddleware listen_publish"""
        pass

    async def send_any(self, subject: str, message, send_func, **kwargs):
        """BarMiddleware send_any"""
        pass

    async def listen_any(self, msg, callback):
        """BarMiddleware listen_any"""
        pass


class FooBarMiddleware(Middleware):
    def __init__(self, foo, bar, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.foo = foo
        self.bar = bar

    def send_any(self, subject: str, message, send_func, **kwargs):
        return f"""FooBarMiddleware send_any params: {self.foo}, {self.bar}"""  # here implemented for testing

    def listen_request(self, msg, callback):
        return f"""FooBarMiddleware listen_request params: {self.foo}, {self.bar}"""


class IncorrectMiddleware:  # not inherited from Middleware
    def send_any(self, msg, send_func):
        pass


class IncSyncMiddleware(Middleware):
    def send_any(self, subject: str, message, send_func, **kwargs):
        message["data"] += 1
        send_func(subject, message, **kwargs)
        message["data"] += 3


class DecSyncMiddleware(Middleware):
    def listen_any(self, msg, callback):
        msg.data -= 1
        callback(msg)
        msg.data -= 3


class IncMiddleware(Middleware):
    async def send_any(self, subject: str, message, send_func, **kwargs):
        message["data"] += 1
        await send_func(subject, message, **kwargs)
        message["data"] += 3


class DecMiddleware(Middleware):
    async def listen_any(self, msg, callback):
        msg.data -= 1
        await callback(msg)
        msg.data -= 3


@pytest.fixture
def app():
    app = panini_app.App(
        service_name="test_middleware_manager",
        host="127.0.0.1",
        port=4222,
    )
    app.nats.middlewares = {
        "send_publish_middleware": [],
        "listen_publish_middleware": [],
        "send_request_middleware": [],
        "listen_request_middleware": [],
    }
    yield app
    app.nats.middlewares = {
        "send_publish_middleware": [],
        "listen_publish_middleware": [],
        "send_request_middleware": [],
        "listen_request_middleware": [],
    }


def test_foo_middleware(app):
    app.add_middleware(FooMiddleware)
    middleware_dict = app.nats.middlewares
    assert len(middleware_dict["send_publish_middleware"]) == 1
    assert len(middleware_dict["send_request_middleware"]) == 0
    assert len(middleware_dict["listen_publish_middleware"]) == 1
    assert len(middleware_dict["listen_request_middleware"]) == 1

    assert (
        middleware_dict["send_publish_middleware"][0].__doc__
        == "FooMiddleware send_publish"
    )
    assert (
        middleware_dict["listen_publish_middleware"][0].__doc__
        == "FooMiddleware listen_publish"
    )
    assert (
        middleware_dict["listen_request_middleware"][0].__doc__
        == "FooMiddleware listen_request"
    )


def test_bar_middleware(app):
    app.add_middleware(BarMiddleware)
    middleware_dict = app.nats.middlewares

    assert len(middleware_dict["send_publish_middleware"]) == 1
    assert len(middleware_dict["send_request_middleware"]) == 1
    assert len(middleware_dict["listen_publish_middleware"]) == 1
    assert len(middleware_dict["listen_request_middleware"]) == 1

    assert (
        middleware_dict["send_publish_middleware"][0].__doc__
        == "BarMiddleware send_any"
    )
    assert (
        middleware_dict["send_request_middleware"][0].__doc__
        == "BarMiddleware send_request"
    )
    assert (
        middleware_dict["listen_publish_middleware"][0].__doc__
        == "BarMiddleware listen_publish"
    )
    assert (
        middleware_dict["listen_request_middleware"][0].__doc__
        == "BarMiddleware listen_any"
    )


def test_foo_bar_middleware(app):
    app.add_middleware(FooBarMiddleware, "foo", bar="bar")
    middleware_dict = app.nats.middlewares
    assert len(middleware_dict["send_publish_middleware"]) == 1
    assert len(middleware_dict["send_request_middleware"]) == 1
    assert len(middleware_dict["listen_publish_middleware"]) == 0
    assert len(middleware_dict["listen_request_middleware"]) == 1

    assert (
        middleware_dict["send_publish_middleware"][0](None, None, None)
        == "FooBarMiddleware send_any params: foo, bar"
    )
    assert (
        middleware_dict["send_request_middleware"][0](None, None, None)
        == "FooBarMiddleware send_any params: foo, bar"
    )
    assert (
        middleware_dict["listen_request_middleware"][0](None, None)
        == "FooBarMiddleware listen_request "
        "params: foo, bar"
    )


def test_multiple_middlewares_order(app):
    app.add_middleware(FooMiddleware)
    app.add_middleware(BarMiddleware)
    app.add_middleware(FooBarMiddleware, "foo", bar="bar")
    middleware_dict = app.nats.middlewares
    assert len(middleware_dict["send_publish_middleware"]) == 3
    assert len(middleware_dict["send_request_middleware"]) == 2
    assert len(middleware_dict["listen_publish_middleware"]) == 2
    assert len(middleware_dict["listen_request_middleware"]) == 3

    assert middleware_dict["send_publish_middleware"][0].__doc__.startswith(
        "FooMiddleware"
    )
    assert middleware_dict["send_publish_middleware"][1].__doc__.startswith(
        "BarMiddleware"
    )
    assert middleware_dict["send_publish_middleware"][2](None, None, None).startswith(
        "FooBarMiddleware"
    )

    assert middleware_dict["send_request_middleware"][0].__doc__.startswith(
        "BarMiddleware"
    )
    assert middleware_dict["send_request_middleware"][1](None, None, None).startswith(
        "FooBarMiddleware"
    )

    assert middleware_dict["listen_publish_middleware"][0].__doc__.startswith(
        "FooMiddleware"
    )
    assert middleware_dict["listen_publish_middleware"][1].__doc__.startswith(
        "BarMiddleware"
    )

    assert middleware_dict["listen_request_middleware"][0].__doc__.startswith(
        "FooMiddleware"
    )
    assert middleware_dict["listen_request_middleware"][1].__doc__.startswith(
        "BarMiddleware"
    )
    assert middleware_dict["listen_request_middleware"][2](None, None).startswith(
        "FooBarMiddleware"
    )


def test_incorrect_middlewares(app):
    with pytest.raises(AssertionError):
        app.add_middleware(IncorrectMiddleware)

    with pytest.raises(TypeError):
        app.add_middleware(
            FooBarMiddleware
        )  # not enough parameters for FooBarMiddleware __init__() method


def test_wrap_function_by_middleware_inc_sync(app):
    def foo(subject, message, **kwargs):
        assert message["data"] == 2
        message["data"] += 2

    app.add_middleware(IncSyncMiddleware)
    for send in ("publish", "request"):
        wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware(send)(foo)
        temp_message = {"data": 1}
        wrapped_function("", temp_message)
        assert temp_message["data"] == 7


def test_wrap_function_by_middleware_dec_sync(app):
    class Bar:
        data = 5
        reply = ""

    def bar(msg):
        assert msg.data == 4
        msg.data -= 2

    app.add_middleware(DecSyncMiddleware)
    wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware("listen")(bar)
    temp_message = Bar()
    wrapped_function(temp_message)
    assert temp_message.data == -1


def test_wrap_function_by_middleware_inc(app):
    async def foo(subject, message, **kwargs):
        assert message["data"] == 2
        message["data"] += 2

    app.add_middleware(IncMiddleware)
    loop = asyncio.get_event_loop()

    for send in ("publish", "request"):
        wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware(send)(foo)
        temp_message = {"data": 1}
        loop.run_until_complete(wrapped_function("", temp_message))
        assert temp_message["data"] == 7


def test_wrap_function_by_middleware_dec(app):
    class Bar:
        data = 5
        reply = ""

    async def bar(msg):
        assert msg.data == 4
        msg.data -= 2

    loop = asyncio.get_event_loop()

    app.add_middleware(DecMiddleware)
    wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware("listen")(bar)
    temp_message = Bar()
    loop.run_until_complete(wrapped_function(temp_message))
    assert temp_message.data == -1


def test_wrap_function_by_middleware_inc_dec_sync(app):
    class Bar:
        data = 5
        reply = "someone"

    def foo(subject, message, **kwargs):
        assert message["data"] == 3
        message["data"] += 2

    def bar(msg):
        assert msg.data == 3
        msg.data -= 2

    app.add_middleware(IncSyncMiddleware)
    app.add_middleware(IncSyncMiddleware)
    app.add_middleware(DecSyncMiddleware)
    app.add_middleware(DecSyncMiddleware)

    for send in ("publish", "request"):
        wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware(send)(foo)
        temp_message = {"data": 1}
        wrapped_function("", temp_message)
        assert temp_message["data"] == 11

    wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware("listen")(bar)
    temp_message = Bar()
    wrapped_function(temp_message)
    assert temp_message.data == -5


def test_wrap_function_by_middleware_inc_dec(app):
    class Bar:
        data = 5
        reply = "someone"

    async def foo(subject, message, **kwargs):
        assert message["data"] == 3
        message["data"] += 2

    async def bar(msg):
        assert msg.data == 3
        msg.data -= 2

    app.add_middleware(IncMiddleware)
    app.add_middleware(IncMiddleware)
    app.add_middleware(DecMiddleware)
    app.add_middleware(DecMiddleware)

    loop = asyncio.get_event_loop()

    for send in ("publish", "request"):
        wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware(send)(foo)
        temp_message = {"data": 1}
        loop.run_until_complete(wrapped_function("", temp_message))
        assert temp_message["data"] == 11

    wrapped_function = app.nats.middleware_manager.wrap_function_by_middleware("listen")(bar)
    temp_message = Bar()
    loop.run_until_complete(wrapped_function(temp_message))
    assert temp_message.data == -5
