import time

from anthill.sandbox import Sandbox
from anthill import app as ant_app


app = ant_app.App(
    service_name='test_publish',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)


@app.task()
async def publish():
    time.sleep(7)
    await app.aio_publish({'data': 1}, topic='foo')

sandbox = Sandbox(app)


def test_publish():
    sandbox.subscribe_new_topic('foo', lambda *args: print(args))


if __name__ == "__main__":
    test_publish()
