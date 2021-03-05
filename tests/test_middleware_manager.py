import pytest

from panini import app as panini_app
from panini.middleware import Middleware


class FooMiddleware(Middleware):
    async def send_publish(self, subject: str, message, publish_func, **kwargs):
        """FooMiddleware send_publish"""  # docstring is important for testing
        pass  # implementation is not important for middleware_dict_factory

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


@pytest.fixture
def app():
    app = panini_app.App(
        service_name="test_middleware_dict_factory",
        host="127.0.0.1",
        port=4222,
    )
    app.MIDDLEWARE = {
        "send_publish_middleware": [],
        "listen_publish_middleware": [],
        "send_request_middleware": [],
        "listen_request_middleware": [],
    }
    return app


def test_foo_middleware(app):
    app.add_middleware(FooMiddleware)
    middleware_dict = app.MIDDLEWARE
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
    middleware_dict = app.MIDDLEWARE

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
    middleware_dict = app.MIDDLEWARE
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
    middleware_dict = app.MIDDLEWARE
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
