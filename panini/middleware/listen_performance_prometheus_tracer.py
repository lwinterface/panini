import time
from copy import deepcopy

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from . import Middleware
from ..app import get_app


class ListenPerformancePrometheusTracerMiddleware(Middleware):
    def __init__(
        self,
        pushgateway_url: str = "localhost:9091",
        app=None,
        frequency: float = 30.0,
        metric_key_suffix: str = "listen_duration",
        job: str = "microservices_activity",
    ):
        if app is None:
            app = get_app()
        assert app is not None
        self.pushgateway_url = pushgateway_url
        self.registry = CollectorRegistry()
        self.metric_key_suffix = metric_key_suffix
        self._empty_subject_report = {
            "min": None,
            "max": None,
            "count": 0,
            "total_duration": 0.0,
        }
        self.report = {}

        def create_gauges(subject: str):
            gauges = {}
            for metric in ("min", "max", "count", "avg"):
                gauges[metric] = Gauge(
                    f"{app.service_name}__{subject.replace('.', '_')}__{metric_key_suffix}__{metric}",
                    f"{metric} duration time",  # description
                    registry=self.registry,
                )
            return gauges

        @app.timer_task(frequency)
        async def push_to_prometheus():
            at_least_one_listen = False
            for subject in self.report:
                report = self.report[subject]
                if report["count"] != 0:
                    at_least_one_listen = True
                    if "gauges" not in report:
                        report["gauges"] = create_gauges(subject)

                    for metric, gauge in report["gauges"].items():
                        if metric == "avg":
                            gauge.set(report["total_duration"] / report["count"])
                        else:
                            gauge.set(report[metric])

                    report.update(deepcopy(self._empty_subject_report))

            if at_least_one_listen:
                push_to_gateway(pushgateway_url, job=job, registry=self.registry)

    async def listen_any(self, msg, callback):
        start_time = time.time()
        await callback(msg)
        duration = time.time() - start_time
        if msg.subject not in self.report:
            self.report[msg.subject] = deepcopy(self._empty_subject_report)

        report = self.report[msg.subject]
        if report["count"] == 0:
            report["max"] = report["min"] = duration
        else:
            report["max"] = max(report["max"], duration)
            report["min"] = min(report["min"], duration)

        report["count"] += 1
        report["total_duration"] += duration
