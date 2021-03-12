import random
import time

from panini import app as panini_app
from panini.middleware.listen_monitoring import (
    ListenMonitoringMiddleware,
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


@app.listen("some.publish.subject")
async def listen(msg):
    log.info(f"Got publish and sleep for {msg.data['time_to_sleep']}")
    time.sleep(msg.data["time_to_sleep"])


if __name__ == "__main__":
    app.add_middleware(ListenMonitoringMiddleware, frequency=4)
    app.start()
