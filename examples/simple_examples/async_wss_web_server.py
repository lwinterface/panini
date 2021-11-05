import uuid
import random
import json
from aiohttp import web
from panini import app as panini_app
from _wss_manager import WSSManager, html

app = panini_app.App(
    service_name="async_NATS_WSS_bridge",
    host='127.0.0.1',
    port=4222,
)
app.setup_web_server(port=5001)
logger = app.logger

async def incoming_messages_callback(subscriber, msg, **kwargs):
    """
    app calls it for each new message from
    NATS and redirects the message
    """
    try:
        await subscriber.send_str(
            json.dumps({"subject": msg.subject, "data": msg.data})
        )
    except Exception as e:
        logger.error(f"error: {str(e)}")

manager = WSSManager(app)
manager.callback = incoming_messages_callback

test_msg = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.0,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}

@app.task(interval=1)
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
    """WebSocket connection """
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connection_id = str(uuid.uuid4())[:10]
    await ws.send_str(json.dumps({"success": True, "data": "Successfully connected"}))
    await manager.client_listener(ws, connection_id)
    try:
        await ws.close()
    except Exception as e:
        logger.error(str(e))
    return ws


async def incoming_messages_callback(subscriber, msg, **kwargs):
    """
    app calls it for each new message from
    NATS and redirects the message
    """
    try:
        await subscriber.send_str(
            json.dumps({"subject": msg.subject, "data": msg.data})
        )
    except Exception as e:
        logger.error(f"error: {str(e)}")


if __name__ == "__main__":
    app.http_server.web_app["subscribers"] = {}
    app.start()
