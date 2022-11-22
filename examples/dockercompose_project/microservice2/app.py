import os
from panini import app as panini_app

app = panini_app.App(
    service_name="microservice2",
    host="nats-server" if "HOSTNAME" in os.environ else "127.0.0.1",
    port=4222,
)

log = app.logger


@app.listen("some.publish.subject")
async def receive_messages(msg):
    log.warning(f"got message {msg.data}")


if __name__ == "__main__":
    app.start()
