import asyncio
import time

from panini import app
from panini.emulator.emulator_client import EmulatorClient
from panini.emulator.reader_emulator_middleware import ReaderEmulatorMiddleware
from panini.utils.helper import start_process

app = app.App(
    service_name="reader",
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


emulator = EmulatorClient('resources/events.writer.2021-03-16-13:06.jsonl', emulate_timeout=False)
app.add_middleware(ReaderEmulatorMiddleware)

if __name__ == "__main__":

    print("app")
    start_process(app.start)
    time.sleep(4)
    print("emulator")
    asyncio.new_event_loop().run_until_complete(emulator.run())

    print("wait")
    asyncio.new_event_loop().run_until_complete(emulator.wait())
    print("done")
