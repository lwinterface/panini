from panini import app as panini_app

app = panini_app.App(
    service_name="js_listen_pull",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0

def get_message():
    return {
        "id": app.nats.client.client_id,
    }


@app.task()
async def subscribe_to_js_stream_pull():
    psub = await app.nats.js_client.pull_subscribe("test.*.stream", durable='consumer-2')
    # Fetch and ack messages from consumer.
    for i in range(0, 10):
        msgs = await psub.fetch(1)
        for msg in msgs:
            print(msg.data)
            await msg.ack()

@app.task(interval=1)
async def subscribe_to_js_stream_pull():
    print('some parallel task')



if __name__ == "__main__":
    app.start()
