import os
from panini import app as panini_app
from panini.middleware.opentracing_middleware import OpenTracingMiddleware

SERVICE_NAME = "microservice2"
JEAGER_HOST = 'jeager:6831' if 'HOSTNAME' in os.environ else '127.0.0.1:6831'

app = panini_app.App(
    service_name=SERVICE_NAME,
    host="nats-server" if "HOSTNAME" in os.environ else "127.0.0.1",
    port=4222,
)

log = app.logger


@app.listen("some.publish.subject")
async def receive_messages(msg):
    log.warning(f"got message: \n - subject: {msg.subject} \n - headers: {msg.headers} \n - data: {msg.data}\n")


if __name__ == "__main__":
    app.add_middleware(
        OpenTracingMiddleware,
        service_name=SERVICE_NAME,
        jeager_host=JEAGER_HOST
    )
    app.start()
