from panini.app import App
from panini.emulator import WriterEmulatorMiddleware, ReaderEmulatorMiddleware

app = App(
    service_name="listener",
    host="127.0.0.1",
    port=4222
)


@app.listen("listener.store.listen")
async def listen(message):
    try:
        print(message.subject, message.data)
    except Exception as ex:
        app.logger.exception(message.subject)


@app.listen("listener.store.request")
async def response(message):
    try:
        print(message.subject, message.data)
        return {"data": "request"}
    except Exception as ex:
        app.logger.exception(message.subject)


if __name__ == "__main__":
    folder = "resources"
    filename = "resources/events.listener.2021-03-17-12:52:07.jsonl"
    app.add_middleware(ReaderEmulatorMiddleware, filename=filename, compare_output=True)
    app.start()
