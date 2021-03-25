import asyncio

from panini.app import App
from panini.emulator import WriterEmulatorMiddleware

app = App(
    service_name="listener_publisher",
    host="127.0.0.1",
    port=4222
)


@app.listen("store.listen")
async def listen(message):
    try:
        print(message.subject, message.data)
    except Exception as ex:
        app.logger.exception(message.subject)


@app.listen("store.request")
async def response(message):
    try:
        print(message.subject, message.data)
        return {"data": "request"}
    except Exception as ex:
        app.logger.exception(message.subject)


@app.task()
async def request_task():
    for i in range(10):
        try:
            response = await app.request("store.request", {"data": f"request.data.{i}"})
            print('response', response)
            await asyncio.sleep(1.5)
        except Exception as ex:
            app.logger.exception(ex)


@app.task()
async def publish_task():
    for i in range(10):
        try:
            await app.publish("store.listen", {"data": f"publish.data.{i}"})
            await asyncio.sleep(1)
        except Exception as ex:
            app.logger.exception(ex)


if __name__ == "__main__":
    folder = "resources"
    filename = "resources/events.listener_publisher.2021-03-19-16-22-26.jsonl"
    app.add_middleware(WriterEmulatorMiddleware, folder=folder)
    app.start()
