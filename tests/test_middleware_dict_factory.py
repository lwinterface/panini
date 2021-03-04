import pytest

from panini import app as panini_app
from panini.middleware import Middleware


class FooMiddleware(Middleware):
    def send_publish(self, msg, publish_func):
        """FooMiddleware send_publish"""  # docstring is important for testing
        pass  # implementation is not important for middleware_dict_factory

    def receive_publish(self, msg, callback):
        """FooMiddleware receive_publish"""
        pass

    def receive_request(self, msg, callback):
        """FooMiddleware receive_request"""
        pass


class BarMiddleware(Middleware):
    def send_request(self, msg, request_func):
        """BarMiddleware send_request"""
        pass

    def receive_publish(self, msg, callback):
        """BarMiddleware receive_publish"""
        pass

    def send_any(self, msg, send_func):
        """BarMiddleware send_any"""
        pass

    def receive_any(self, msg, callback):
        """BarMiddleware receive_any"""
        pass


class FooBarMiddleware(Middleware):
    def __init__(self, foo, bar, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.foo = foo
        self.bar = bar

    def send_any(self, msg, send_func):
        return f"""FooBarMiddleware send_any params: {self.foo}, {self.bar}"""  # here implemented for testing

    def receive_request(self, msg, callback):
        return f"""FooBarMiddleware receive_request params: {self.foo}, {self.bar}"""


class IncorrectMiddleware:  # not inherited from Middleware
    def send_any(self, msg, send_func):
        pass


@pytest.fixture
def app():
    return panini_app.App(
        service_name="test_middleware_dict_factory",
        host="127.0.0.1",
        port=4222,
    )


def test_foo_middleware(app):
    app.add_middleware(FooMiddleware)
    middleware_dict = app.get_middleware_dict()
    assert len(middleware_dict["send_publish_middleware"]) == 1
    assert len(middleware_dict["send_request_middleware"]) == 0
    assert len(middleware_dict["receive_publish_middleware"]) == 1
    assert len(middleware_dict["receive_request_middleware"]) == 1

    assert (
        middleware_dict["send_publish_middleware"][0].__doc__
        == "FooMiddleware send_publish"
    )
    assert (
        middleware_dict["receive_publish_middleware"][0].__doc__
        == "FooMiddleware receive_publish"
    )
    assert (
        middleware_dict["receive_request_middleware"][0].__doc__
        == "FooMiddleware receive_request"
    )


def test_bar_middleware(app):
    app.add_middleware(BarMiddleware)
    middleware_dict = app.get_middleware_dict()

    assert len(middleware_dict["send_publish_middleware"]) == 1
    assert len(middleware_dict["send_request_middleware"]) == 1
    assert len(middleware_dict["receive_publish_middleware"]) == 1
    assert len(middleware_dict["receive_request_middleware"]) == 1

    assert (
        middleware_dict["send_publish_middleware"][0].__doc__
        == "BarMiddleware send_any"
    )
    assert (
        middleware_dict["send_request_middleware"][0].__doc__
        == "BarMiddleware send_request"
    )
    assert (
        middleware_dict["receive_publish_middleware"][0].__doc__
        == "BarMiddleware receive_publish"
    )
    assert (
        middleware_dict["receive_request_middleware"][0].__doc__
        == "BarMiddleware receive_any"
    )


def test_foo_bar_middleware(app):
    app.add_middleware(FooBarMiddleware, "foo", bar="bar")
    middleware_dict = app.get_middleware_dict()
    assert len(middleware_dict["send_publish_middleware"]) == 1
    assert len(middleware_dict["send_request_middleware"]) == 1
    assert len(middleware_dict["receive_publish_middleware"]) == 0
    assert len(middleware_dict["receive_request_middleware"]) == 1

    assert (
        middleware_dict["send_publish_middleware"][0](None, None)
        == "FooBarMiddleware send_any params: foo, bar"
    )
    assert (
        middleware_dict["send_request_middleware"][0](None, None)
        == "FooBarMiddleware send_any params: foo, bar"
    )
    assert (
        middleware_dict["receive_request_middleware"][0](None, None)
        == "FooBarMiddleware receive_request "
        "params: foo, bar"
    )


def test_multiple_middlewares_order(app):
    app.add_middleware(FooMiddleware)
    app.add_middleware(BarMiddleware)
    app.add_middleware(FooBarMiddleware, "foo", bar="bar")
    middleware_dict = app.get_middleware_dict()
    assert len(middleware_dict["send_publish_middleware"]) == 3
    assert len(middleware_dict["send_request_middleware"]) == 2
    assert len(middleware_dict["receive_publish_middleware"]) == 2
    assert len(middleware_dict["receive_request_middleware"]) == 3

    assert middleware_dict["send_publish_middleware"][0].__doc__.startswith(
        "FooMiddleware"
    )
    assert middleware_dict["send_publish_middleware"][1].__doc__.startswith(
        "BarMiddleware"
    )
    assert middleware_dict["send_publish_middleware"][2](None, None).startswith(
        "FooBarMiddleware"
    )

    assert middleware_dict["send_request_middleware"][0].__doc__.startswith(
        "BarMiddleware"
    )
    assert middleware_dict["send_request_middleware"][1](None, None).startswith(
        "FooBarMiddleware"
    )

    assert middleware_dict["receive_publish_middleware"][0].__doc__.startswith(
        "FooMiddleware"
    )
    assert middleware_dict["receive_publish_middleware"][1].__doc__.startswith(
        "BarMiddleware"
    )

    assert middleware_dict["receive_request_middleware"][0].__doc__.startswith(
        "FooMiddleware"
    )
    assert middleware_dict["receive_request_middleware"][1].__doc__.startswith(
        "BarMiddleware"
    )
    assert middleware_dict["receive_request_middleware"][2](None, None).startswith(
        "FooBarMiddleware"
    )


def test_incorrect_middlewares(app):
    with pytest.raises(AssertionError):
        app.add_middleware(IncorrectMiddleware)

    with pytest.raises(TypeError):
        app.add_middleware(
            FooBarMiddleware
        )  # not enough parameters for FooBarMiddleware __init__() method
        app.get_middleware_dict()
