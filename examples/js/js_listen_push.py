from panini import app as panini_app

app = panini_app.App(
    service_name="js_listen_push",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0

@app.task()
async def subscribe_to_js_stream_push():
    async def cb(msg):
        log.info(f"got JS message ! {msg.subject}:{msg.data}")

    await app.nats.js_client.subscribe("test.*.stream", cb=cb, durable='consumer-1', stream="sample-stream-1")


if __name__ == "__main__":
    app.start()
