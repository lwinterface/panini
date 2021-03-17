import random
import asyncio

from panini import app as panini_app
from panini.middleware.prometheus_monitoring import (
    PrometheusMonitoringMiddleware,
)

app = panini_app.App(
    service_name="async_listen_monitoring_middleware",
    host="127.0.0.1",
    port=4222,
)

log = app.logger


@app.timer_task(2)
async def publish():
    await app.publish("some.publish.subject", {"time_to_sleep": random.random()})


@app.timer_task(7)
async def publish():
    await app.publish("another.publish.subject", {"time_to_sleep": random.random() * 4})


@app.timer_task(5)
async def publish():
    await app.request(
        "additional.request.subject", {"time_to_sleep": random.random() * 5}
    )


@app.listen("some.publish.subject")
async def listen(msg):
    log.info(f"Got publish and sleep for {msg.data['time_to_sleep']}")
    await asyncio.sleep(msg.data["time_to_sleep"])


@app.listen("another.publish.subject")
async def listen(msg):
    log.info(f"Another got publish and sleep for {msg.data['time_to_sleep']}")
    await asyncio.sleep(msg.data["time_to_sleep"])


@app.listen("additional.request.subject")
async def listen(msg):
    return await app.request("error.request.subject", msg.data)


@app.listen("error.request.subject")
async def listen(msg):
    log.info(f"Another got request and sleep for {msg.data['time_to_sleep']}")
    a = 1 // 0  # raise an error
    await asyncio.sleep(msg.data["time_to_sleep"])
    return {"data": a}


if __name__ == "__main__":
    app.add_middleware(PrometheusMonitoringMiddleware, frequency=5)
    app.start()
