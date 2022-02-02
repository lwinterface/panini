from panini import app as panini_app

app = panini_app.App(
    service_name="js_listen_pull",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0

@app.on_start_task()
async def on_start_task():
    # Persist messages on 'foo's subject.
    await app.nats.js_client.add_stream(name="sample-stream-3", subjects=["test.*.stream"])


def get_message():
    return {
        "id": app.nats.client.client_id,
    }


@app.task()
async def subscribe_to_js_stream_pull():
    psub = await app.nats.js_client.pull_subscribe("test.*.stream", "psub")

    # Fetch and ack messagess from consumer.
    for i in range(0, 10):
        msgs = await psub.fetch(1)
        for msg in msgs:
            print(msg.data)
    print('success!')



if __name__ == "__main__":
    app.start()
