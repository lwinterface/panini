### Monitoring System Performance with Prometheus & Grafana

Do you want to gain more insight into the performance of your system? With Prometheus and Grafana, it's easy to monitor key metrics and get a comprehensive view of what is occurring within your system.

We are using [Prometheus](https://prometheus.io/), a time-series database and monitoring solution, and [Grafana](https://grafana.com/), a user-friendly dashboard, to collect and visualize important metrics. The Panini built-in [Prometheus Monitoring Middleware](https://github.com/lwinterface/panini/blob/master/panini/middleware/prometheus_monitoring.py) is used to collect message rate by subject, request status, and request latency. After collecting, it periodically sends these metrics to the Prometheus Gateway, which is reflected directly in your Grafana dashboard.

### Initializing the Monitoring

Firstly, ensure that you have Prometheus and Grafana up and running. Next, add the Prometheus Monitoring Middleware to the app:

```python
from panini.middleware.prometheus_middleware import PrometheusMonitoringMiddleware

app.add_middleware(PrometheusMonitoringMiddleware)
# you could also specify some custom parameters (see details in middleware constructor):
# app.add_middleware(PrometheusMonitoringMiddleware, PROMETHEUS_GATEWAY, frequency=30)
```

**PrometheusMonitoringMiddleware** parameters:

- pushgateway_url: str = "[localhost:9091](http://localhost:9091)" - url to Prometheus PushGateway
- app = None - panini App

When this is done, application activity will be stored in Prometheus and reflected in the Grafana dashboard.

### Using Grafana & Prometheus

You can use our [dashboard](https://github.com/lwinterface/panini/tree/master/grafana_dashboard) template or create your own. To get started, check out this screenshot of the dashboard 

![https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2Fb1765716-a820-4878-8112-fa05fb301aa2%2FScreenshot_2021-04-03_at_18.50.32.png?table=block&id=5b003b2e-9a68-41ad-ad49-ce2e2035d60f&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=2000&userId=&cache=v2](https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2Fb1765716-a820-4878-8112-fa05fb301aa2%2FScreenshot_2021-04-03_at_18.50.32.png?table=block&id=5b003b2e-9a68-41ad-ad49-ce2e2035d60f&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=2000&userId=&cache=v2)

To learn more about setting up Grafana & Prometheus, take a look at our [guide](https://example.com).