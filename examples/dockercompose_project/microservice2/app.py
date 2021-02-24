from panini import app as panini_app

app = panini_app.App(
    service_name="microservice2",
    host="127.0.0.1",
    port=4222,
    app_strategy="asyncio",
)

log = app.logger.log


@app.listen("some.publish.topic")
async def receive_messages(topic, message):
    log(f"got message {message}")


if __name__ == "__main__":
    app.start()
