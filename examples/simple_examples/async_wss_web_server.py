import uuid
import random
import json
from aiohttp import web
from panini import app as panini_app
from examples.simple_examples._wss_manager import WSSManager, html


app = panini_app.App(
    service_name="async_NATS_WSS_bridge",
    # host='nats-server' if 'HOSTNAME' in os.environ else '127.0.0.1',
    host="54.36.108.188",
    port=4222,
    app_strategy="asyncio",
    web_server=True,
    web_port=1111,
)
log = app.logger
test_msg = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.0,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}

manager = WSSManager(app)


@app.timer_task(interval=1)
async def publish_periodically_for_test():
    test_msg["key3"] = random.random()
    await app.publish("test.subject", test_msg)


@app.http.get("/")
async def web_endpoint_listener(request):
    """
    Web client to view NATS stream. Displays messages from subjects that an user is following

    Example of request
    subscribe:
    {"subjects":["*.>"],"action":"subscribe"}
    unsubscribe:
    {"subjects":["*.>"],"action":"unsubscribe"}

    """
    return web.Response(text=html, content_type="text/html")


@app.http.get("/stream")
async def web_endpoint_listener(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connection_id = str(uuid.uuid4())[:10]
    await ws.send_str(json.dumps({"success": True, "data": "Successfully connected"}))
    await manager.client_listener(ws, connection_id)
    try:
        await ws.close()
    except Exception as e:
        log.error(str(e))
    return ws


async def incoming_messages_callback(subscriber, msg, **kwargs):
    try:
        await subscriber.send_str(
            json.dumps({"subject": msg.subject, "data": msg.data})
        )
    except Exception as e:
        log.error(f"error: {str(e)}")


if __name__ == "__main__":
    manager.callback = incoming_messages_callback
    app.http_server.web_app["subscribers"] = {}
    app.start()
