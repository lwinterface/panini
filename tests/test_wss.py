import asyncio
import uuid
import json
import time

import pytest
from aiohttp import web
from panini import app as panini_app
from panini.test_client import TestClient
from examples.simple_examples._wss_manager import WSSManager


def run_panini():
    app = panini_app.App(
        service_name="test_wss",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False
    )

    app.setup_web_server(port=5001)
    manager = WSSManager(app)

    @app.listen("test_wss.start")
    async def publish(msg):
        await app.publish(subject="test_wss.foo.bar", message={"data": 1}, force=True)

    @app.http.get("/test_wss/stream")
    async def web_endpoint_listener(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        connection_id = str(uuid.uuid4())[:10]
        await ws.send_str(
            json.dumps({"success": True, "message": "Successfully connected"})
        )
        await manager.client_listener(ws, connection_id)
        await ws.close()
        return ws

    async def incoming_messages_callback(subscriber, msg):
        await subscriber.send_str(
            json.dumps({"subject": msg.subject, "data": msg.data})
        )

    manager.callback = incoming_messages_callback
    app.http_server.web_app["subscribers"] = {}
    app.start()


@pytest.fixture(scope="module")
def client():
    # provide parameter for using web_socket - use_web_socket;
    client = TestClient(run_panini=run_panini, use_web_socket=True)
    client.start()
    yield client
    client.stop()


def test_wss_bridge(client):
    print("Before connect")
    time.sleep(1)
    client.websocket_session.connect("ws://127.0.0.1:5001/test_wss/stream")
    print("Connected")
    subscribe_message = {
        "subjects": ["test_wss.foo.bar"],
        "action": "subscribe",
    }  # subscribe to all subjects with .
    client.websocket_session.send(json.dumps(subscribe_message))
    response = json.loads(client.websocket_session.recv())
    assert response["success"] is True
    assert response["message"] == "Successfully connected"

    response = json.loads(client.websocket_session.recv())
    print(response)
    assert response["message"] == "Successfully connected to events: 'test_wss.foo.bar'"

    client.publish("test_wss.start", {})
    response = json.loads(client.websocket_session.recv())["data"]
    assert response["data"] == 1

    unsubscribe_message = {
        "subjects": ["test_wss.foo.bar"],
        "action": "unsubscribe",
    }  # unsubscribe
    client.websocket_session.send(json.dumps(unsubscribe_message))
    response = json.loads(client.websocket_session.recv())

    assert response["success"] is True
    assert response["message"] == "Successfully unsubscribed from event: test_wss.foo.bar"

    client.websocket_session.close()
