### Overview

In terms of microservices, when it is a bit harder to get the full image of what is going on, we decided to implement the built-in possibility to watch the performance and find out problems or bugs in the system easier and faster.

For this stuff we are using:

- [**Prometheus** ](https://prometheus.io/)time-series database & monitoring solution.
- [**Grafana** ](https://grafana.com/) for user-friendly dashboards.
- Panini built-in [**middleware** ](https://www.notion.so/Middlewares-a9dcd04247514c9cb05b9823f68b223b) [PrometheusMonitoringMiddleware](https://github.com/lwinterface/panini/blob/master/panini/middleware/prometheus_monitoring.py)

The main idea of **PrometheusMonitoringMiddleware** is to collect important metrix, such as:

- Message **rate** by subject
- Request **status** (success or failure)
- Request **latency**

After collecting, it will pereodically send these metrixes to [Prometheus Gateway](https://prometheus.io/docs/instrumenting/pushing/), so you will see the changes in your Grafana dashboard *live.*

### Initialize monitoring in Panini application

Suppose, that we already have **Prometheus** & **Grafana** up and running.

After that, we need to add **PrometheusMonitoringMiddleware** to the app:

```python
from panini.middleware.prometheus_middleware import PrometheusMonitoringMiddleware

app.add_middleware(PrometheusMonitoringMiddleware)
# you could also specify some custom parameters (see details in middleware constructor):
# app.add_middleware(PrometheusMonitoringMiddleware, PROMETHEUS_GATEWAY, frequency=30)
```

**PrometheusMonitoringMiddleware** parameters:

- pushgateway_url: str = "[localhost:9091](http://localhost:9091)" - url to Prometheus PushGateway
- app = None - panini App, from which the

After this, all important activity of your application will be stored in Prometheus and user-friendly demonstrated in Grafana dashboard.

### How to use Grafana to watch it

Below our [dashboard](https://github.com/lwinterface/panini/tree/master/grafana_dashboard) that you can get here:

![https://www.notion.so/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2Fb1765716-a820-4878-8112-fa05fb301aa2%2FScreenshot_2021-04-03_at_18.50.32.png?table=block&id=da0151aa-b974-4ca2-882c-a239923fe5ce&width=3070&userId=&cache=v2](https://www.notion.so/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2Fb1765716-a820-4878-8112-fa05fb301aa2%2FScreenshot_2021-04-03_at_18.50.32.png?table=block&id=da0151aa-b974-4ca2-882c-a239923fe5ce&width=3070&userId=&cache=v2)

You can just use our template, or dig into Grafana for more custom approach.