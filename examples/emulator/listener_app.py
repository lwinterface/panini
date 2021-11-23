from panini.app import App

from panini.middleware.reader_emulator_middleware import ReaderEmulatorMiddleware
from panini.managers.nats_client import Msg

app = App(service_name="listener", host="127.0.0.1", port=4222)


@app.listen("listener.store.listen")
async def listen(message: Msg):
    try:
        print(message.subject, message.data)
    except Exception:
        app.logger.exception(message.subject)


@app.listen("listener.store.request")
async def response(message: Msg):
    try:
        print(message.subject, message.data)
        return {"data": "request"}
    except Exception:
        app.logger.exception(message.subject)


if __name__ == "__main__":
    folder = "resources"
    filename = "resources/events.listener.2021-03-22-16-30-18.jsonl"
    # app.add_middleware(WriterEmulatorMiddleware, folder=folder)
    app.add_middleware(ReaderEmulatorMiddleware, filename=filename)
    # app.add_middleware(ReaderEmulatorMiddleware, prefix='prefix', run_emulator=False)
    app.start()
