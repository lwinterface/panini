### Overview

With microservices, it can be challenging to get a comprehensive view of what is occurring within your system. We decided to implement the built-in possibility to monitor performance in order to reveal problems or bugs in the system faster and simpler.

We are using:

- [**Prometheus**](https://prometheus.io/) time-series database & monitoring solution.
- [**Grafana**](https://grafana.com/) for user-friendly dashboards.
- Panini built-in [**middleware**](/Middlewares) [PrometheusMonitoringMiddleware](https://github.com/lwinterface/panini/blob/master/panini/middleware/prometheus_monitoring.py)

The main idea of **PrometheusMonitoringMiddleware** is to collect important metrics, such as:

- Message **rate** by subject
- Request **status** (success or failure)
- Request **latency**

After collecting, it periodically sends these metrics to [Prometheus Gateway](https://prometheus.io/docs/instrumenting/pushing/) that reflected directly in your Grafana dashboard*.*

### Initializing the monitoring

Suppose that we already have **Prometheus** & **Grafana** up and running.

After that, we need to add **PrometheusMonitoringMiddleware** to the app:

```python
from panini.middleware.prometheus_middleware import PrometheusMonitoringMiddleware

app.add_middleware(PrometheusMonitoringMiddleware)
# you could also specify some custom parameters (see details in middleware constructor):
# app.add_middleware(PrometheusMonitoringMiddleware, PROMETHEUS_GATEWAY, frequency=30)
```

**PrometheusMonitoringMiddleware** parameters:

- pushgateway_url: str = "[localhost:9091](http://localhost:9091)" - url to Prometheus PushGateway
- app = None - panini App

After this, application activity will be stored in Prometheus and demonstrated in the Grafana dashboard.

### Using Grafana & Prometheus

Below is our [dashboard](https://github.com/lwinterface/panini/tree/master/grafana_dashboard) that you can get here:

![https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2Fb1765716-a820-4878-8112-fa05fb301aa2%2FScreenshot_2021-04-03_at_18.50.32.png?table=block&id=5b003b2e-9a68-41ad-ad49-ce2e2035d60f&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=2000&userId=&cache=v2](https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2Fb1765716-a820-4878-8112-fa05fb301aa2%2FScreenshot_2021-04-03_at_18.50.32.png?table=block&id=5b003b2e-9a68-41ad-ad49-ce2e2035d60f&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=2000&userId=&cache=v2)

You can use our template or dig into Grafana for a more custom approach.

How to set up Grafana & Prometheus <here>