from dataclasses import dataclass
from typing import Optional, Callable
from nats.js import api


@dataclass
class Listen:
    callback: Callable
    subject: str
    data_type: type = dict
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
        subject: list or str,
        data_type: type = dict,
        **kwargs
    ):
        def wrapper(callback):
            if isinstance(subject, list):
                for s in subject:
                    self._create_subscription_if_missing(s)
                    listen_obj = Listen(
                        callback=callback,
                        subject=s,
                        data_type=data_type,
                        **kwargs
                    )
                    self._subscriptions[s].append(listen_obj)
            else:
                self._create_subscription_if_missing(subject)
                listen_obj = Listen(
                    callback=callback,
                    subject=subject,
                    data_type=data_type,
                    **kwargs
                )
                self._subscriptions[subject].append(listen_obj)
            return callback
        return wrapper

    def js_listen(
        self,
        subject: list or str,
        data_type: type = dict,
        **kwargs,
    ):
        def wrapper(callback):
            self._create_subscription_if_missing(subject, js=True)
            js_listen_obj = JsListen(
                callback=callback,
                subject=subject,
                data_type=data_type,
                **kwargs
            )
            self._js_subscriptions[subject].append(js_listen_obj)
            return callback
        return wrapper


    def _create_subscription_if_missing(self, subscription, js=False):
        if js:
            if subscription not in self._js_subscriptions:
                self._js_subscriptions[subscription] = []
        else:
            if subscription not in self._subscriptions:
                self._subscriptions[subscription] = []
