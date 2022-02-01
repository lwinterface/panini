from panini import app as panini_app

app = panini_app.App(
    service_name="js_listen_push",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0

@app.on_start_task()
async def on_start_task():
    # Persist messages on 'foo's subject.
    await app.nats.js_client.add_stream(name="sample-stream-2", subjects=["test.*.stream"])


def get_message():
    return {
        "id": app.nats.client.client_id,
    }



@app.task()
async def subscribe_to_js_stream_push():
    async def cb(msg):
        log.info(f"got JS message ! {msg.subject}:{msg.data}")
    await app.nats.js_client.subscribe("test.*.stream", cb=cb)



if __name__ == "__main__":
    app.start()
