from panini import app as panini_app

app = panini_app.App(
    service_name="js_publish",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0


@app.on_start_task()
async def on_start_task():
    # Persist messages on 'test.*.stream' subject.
    await app.nats.js_client.add_stream(name="sample-stream-1", subjects=["test.*.stream"])


def get_message():
    return {
        "id": app.nats.client.client_id,
    }


@app.timer_task(interval=2)
async def publish_periodically():
    subject = "test.app2.stream"
    message = get_message()
    global NUM
    NUM+=1
    message['counter'] = NUM
    await app.publish(subject=subject, message=message)
    log.info(f"sent {message}")



if __name__ == "__main__":
    app.start()
