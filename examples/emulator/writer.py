import asyncio
from datetime import datetime

from panini.emulator.writer_emulator_middleware import WriterEmulatorMiddleware
from panini.app import App

app = App(
    service_name="writer",
    host="127.0.0.1",
    port=4222
)


@app.listen("store.listen")
async def listen(message):
    try:
        pass
    except Exception as ex:
        app.logger.exception(message.subject)


@app.listen("store.request")
async def response(message):
    try:
        return {"data": "request"}
    except Exception as ex:
        app.logger.exception(message.subject)


@app.task()
async def request_task():
    for i in range(10):
        subject = "store.request"
        try:
            await app.request(subject, {"data": f"request.data.{i}"})
            await asyncio.sleep(3)
        except Exception as ex:
            app.logger.exception(subject)
    print("finish request")

@app.task()
async def publish_task():
    for i in range(10):
        subject = "store.listen"
        try:
            await app.publish(subject, {"data": f"publish.data.{i}"})
            await asyncio.sleep(2)
        except Exception as ex:
            app.logger.exception(subject)
    print("finish publish")

if __name__ == "__main__":
    events_filename = f"resources/events.{app.service_name}.{datetime.now().strftime('%Y-%m-%d-%H:%M')}.jsonl"
    app.add_middleware(WriterEmulatorMiddleware, filename=events_filename)
    app.start()
