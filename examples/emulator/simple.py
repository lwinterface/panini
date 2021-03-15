import asyncio
import time

from panini import app
from panini.emulator.emulator_client import EmulatorClient

app = app.App(
    service_name="test_emulator",
    host="127.0.0.1",
    port=4222,
    web_server=True
)


@app.listen("test_middleware.publish")
async def publish(msg):
    try:
        await app.publish(
            subject="test_middleware.publish.response",
            message={"data": msg.data["data"] + 1},
        )
    except Exception:
        app.logger.exception("test_middleware.publish")


@app.listen("test_middleware.request")
async def request(msg):
    try:
        response = await app.request(
            subject="test_middleware.request.helper",
            message={"data": msg.data["data"]},
        )
        return {"data": response["data"] + 2}
    except Exception:
        app.logger.exception("test_middleware.request")


@app.listen("test_middleware.request.helper")
async def helper(msg):
    try:
        return {"data": msg.data["data"] + 2}
    except Exception:
        app.logger.exception("test_middleware.request.helper")


@app.listen("test_middleware.listen.publish")
async def request(msg):
    try:
        await app.publish(
            subject="test_middleware.listen.publish.response",
            message={"data": msg.data["data"] + 3},
        )
    except Exception:
        app.logger.exception("test_middleware.listen.publish")


@app.listen("test_middleware.listen.request")
async def request(msg):
    try:
        return {"data": msg.data["data"] + 4}
    except Exception:
        app.logger.exception("test_middleware.listen.request")


emulator = EmulatorClient('resources/events.jsonl')


if __name__ == "__main__":

    print("emulator")
    asyncio.new_event_loop().run_until_complete(emulator.run())
    # print("app")
    # app.start(from_another_thread=True)
    print("wait")
    asyncio.new_event_loop().run_until_complete(emulator.wait())
    print("done")
