__version__ = '0.1.0'
from aiohttp import web
from panini import app as panini_app



app = panini_app.App(
    service_name="async_web_server_with_periodic_task",
    host='127.0.0.1',
    port=4222,
)
app.setup_web_server(port=8081)
log = app.logger
NUM = 0

def get_message():
    return {
        "version": __version__,
        "name": app.nats.client_id,
        "id": app.nats.client.client_id,
        "NATS_brokers": app.nats.servers,
}


@app.task()
async def publish():
    message = {"event": "app started!"}
    await app.publish(subject="some.request.subject", message=message)
    log.info(str(message))

@app.timer_task(interval=2)
async def publish_periodically():
    subject = "test.app1.stream"
    global NUM
    NUM+=1
    message = get_message()
    message['counter'] = NUM
    await app.publish(subject=subject, message=message)
    log.info(f"sent {message}")

@app.http.get("/profile")
async def web_endpoint_listener(request):
    """
    Single HTTP endpoint
    """
    message = get_message()
    message['counter'] = NUM
    return web.Response(text=str(message))



if __name__ == "__main__":
    app.start()
