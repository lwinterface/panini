import time

from prometheus_client import CollectorRegistry, Histogram, Counter, push_to_gateway
from prometheus_client.utils import INF
from nats.aio.errors import ErrTimeout

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

DEFAULT_LABELS = (
    "app_name",
    "client_id",
    "subject",
    "status",
)


class PrometheusMonitoringMiddleware(Middleware):
    def __init__(
        self,
        pushgateway_url: str = "localhost:9091",
        app=None,
        frequency: float = 10.0,
        job: str = "microservices_activity",
        buckets: tuple = DEFAULT_BUCKETS,
        labels: tuple = DEFAULT_LABELS,
    ):
        if app is None:
            app = get_app()
        assert app is not None, "App must be initialized before this middleware"
        self.pushgateway_url = pushgateway_url
        self.registry = CollectorRegistry()
        self.app_name = app.service_name
        self.app_client_id = app.client_id
        self.buckets = buckets
        assert set(labels).issubset(
            set(DEFAULT_LABELS)
        ), f"Labels must be in {DEFAULT_LABELS}"
        self.labels = labels
        self.listen_counter = self.create_listen_counter()
        self.listen_latency_histogram = self.create_listen_latency_histogram()

        @app.timer_task(frequency)
        async def push_to_prometheus():
            push_to_gateway(pushgateway_url, job=job, registry=self.registry)

    def create_listen_counter(self):
        counter = Counter(
            "panini_listen_total",
            "Listen duration in seconds",  # description
            registry=self.registry,
            labelnames=self.labels,
        )
        return counter

    def create_listen_latency_histogram(self):
        histogram = Histogram(
            "panini_listen_latency_seconds",
            "Listen duration in seconds",  # description
            registry=self.registry,
            buckets=self.buckets,
            labelnames=self.labels,
        )
        return histogram

    def monitor_listen(self, start_time: float, labels: dict):
        duration = time.time() - start_time
        labels = {
            label_key: label_value
            for label_key, label_value in labels.items()
            if label_key in self.labels
        }
        self.listen_counter.labels(**labels).inc()
        self.listen_latency_histogram.labels(**labels).observe(duration)

    async def listen_any(self, msg, callback):
        labels = {
            "app_name": self.app_name,
            "client_id": self.app_client_id,
            "subject": msg.subject,
        }

        start_time = time.time()

        if "status" in self.labels:
            try:
                response = await callback(msg)
            except Exception:
                labels["status"] = "failure"
                self.monitor_listen(start_time, labels)
                raise
            else:
                labels["status"] = "success"
        else:
            response = await callback(msg)

        self.monitor_listen(start_time, labels)

        return response
