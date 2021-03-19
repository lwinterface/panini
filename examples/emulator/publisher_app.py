import asyncio

from panini.app import App
from panini.emulator import WriterEmulatorMiddleware
from panini.emulator import ReaderEmulatorMiddleware
from panini.middleware.nats_timeout import NATSTimeoutMiddleware

app = App(
    service_name="publisher",
    host="127.0.0.1",
    port=4222
)


@app.task()
async def request_task():
    for i in range(10):
        try:
            print("request listener.store.request")

            response = await app.request("listener.store.request", {"data": f"request.data.{i}"})
            print('response', response)
            await asyncio.sleep(1.5)
        except Exception as ex:
            app.logger.exception(ex)


@app.task()
async def publish_task():
    for i in range(10):
        try:
            print("publish listener.store.listen")
            await app.publish("listener.store.listen", {"data": f"publish.data.{i}"})
            await asyncio.sleep(1)
        except Exception as ex:
            app.logger.exception(ex)


if __name__ == "__main__":
    folder = "resources"
    filename = "events.publisher.2021-03-19-16:21:30.jsonl"
    app.add_middleware(ReaderEmulatorMiddleware, folder=folder, filename=f"{folder}/{filename}", compare_output=True)
    app.start()
