import time

from prometheus_client import CollectorRegistry, Histogram, push_to_gateway
from prometheus_client.utils import INF

from . import Middleware
from ..app import get_app


DEFAULT_BUCKETS = (
    0.001,
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
    INF,
)


class ListenMonitoringMiddleware(Middleware):
    def __init__(
        self,
        pushgateway_url: str = "localhost:9091",
        app=None,
        frequency: float = 10.0,
        job: str = "microservices_activity",
        buckets=DEFAULT_BUCKETS,
    ):
        if app is None:
            app = get_app()
        assert app is not None
        self.pushgateway_url = pushgateway_url
        self.registry = CollectorRegistry()
        self.app_name = app.service_name
        self.app_client_id = app._client_id
        self.buckets = buckets
        self.histogram = self.create_histogram()

        @app.timer_task(frequency)
        async def push_to_prometheus():
            push_to_gateway(pushgateway_url, job=job, registry=self.registry)

    def create_histogram(self):
        histogram = Histogram(
            "microservices_listen_latency_seconds",
            "Listen duration in seconds",  # description
            registry=self.registry,
            buckets=self.buckets,
            labelnames=("app_name", "client_id", "subject"),
        )
        return histogram

    async def listen_any(self, msg, callback):
        start_time = time.time()
        response = await callback(msg)
        duration = time.time() - start_time

        self.histogram.labels(
            app_name=self.app_name, client_id=self.app_client_id, subject=msg.subject
        ).observe(duration)

        return response
