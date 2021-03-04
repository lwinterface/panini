from typing import NamedTuple


class Middleware:
    def __init__(self, *args, **kwargs):
        pass

    def send_publish(self, msg, publish_func):
        """
        :param msg: NatsMessage to send
        :param publish_func: Callable for publish
        :return: None
        """
        pass

    def receive_publish(self, msg, callback):
        """
        :param msg: NatsMessage to receive
        :param callback: Callable, that called on receive
        :return: None
        """
        pass

    def send_request(self, msg, request_func):
        """
        :param msg: NatsMessage to send
        :param request_func: Callable for request
        :return: NatsMessage response
        """
        pass

    def receive_request(self, msg, callback):
        """
        :param msg: NatsMessage to receive
        :param callback: Callable, that called on receive
        :return: NatsMessage response
        """
        pass

    def send_any(self, msg, send_func):
        """
        :param msg: NatsMessage to send
        :param send_func: Callable for send
        :return: NatsMessage or None response
        """
        pass

    def receive_any(self, msg, callback):
        """
        :param msg: NatsMessage to receive
        :param callback: Callable, that called on receive
        :return: NatsMessage or None response
        """
        pass


def middleware_dict_factory(middleware_list: [NamedTuple]) -> dict:
    """Split middlewares for each specific purpose into middleware dict"""
    middleware_dict = {
        "send_publish_middleware": [],
        "receive_publish_middleware": [],
        "send_request_middleware": [],
        "receive_request_middleware": [],
    }
    for middleware in middleware_list:
        assert issubclass(
            middleware.cls, Middleware
        ), "Each custom middleware class must be a subclass of Middleware"
        high_priority_functions = (
            "send_publish",
            "receive_publish",
            "send_request",
            "receive_request",
        )
        global_functions = ("send_any", "receive_any")

        # check, that at least one function is implemented
        assert any(
            function in middleware.cls.__dict__
            for function in high_priority_functions + global_functions
        ), f"At least one of the following functions must be implemented: {high_priority_functions + global_functions}"

        middleware_obj = middleware.cls(*middleware.args, **middleware.kwargs)
        for function_name in high_priority_functions:
            if function_name in middleware.cls.__dict__:
                middleware_dict[f"{function_name}_middleware"].append(
                    getattr(middleware_obj, function_name)
                )

        if "send_any" in middleware.cls.__dict__:
            if "send_publish" not in middleware.cls.__dict__:
                middleware_dict[f"send_publish_middleware"].append(
                    middleware_obj.send_any
                )

            if "send_request" not in middleware.cls.__dict__:
                middleware_dict[f"send_request_middleware"].append(
                    middleware_obj.send_any
                )

        if "receive_any" in middleware.cls.__dict__:
            if "receive_publish" not in middleware.cls.__dict__:
                middleware_dict[f"receive_publish_middleware"].append(
                    middleware_obj.receive_any
                )

            if "receive_request" not in middleware.cls.__dict__:
                middleware_dict[f"receive_request_middleware"].append(
                    middleware_obj.receive_any
                )

    return middleware_dict
