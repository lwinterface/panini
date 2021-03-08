import uuid
import json

import pytest
from aiohttp import web
from panini import app as ant_app
from panini.test_client import TestClient
from examples.simple_examples._wss_manager import WSSManager
from tests.helper import get_testing_logs_directory_path


def run_panini():
    app = ant_app.App(
        service_name="async_NATS_WSS_bridge",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        web_server=True,
        web_port=1111,
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    manager = WSSManager(app)

    @app.listen("start")
    async def publish(msg):
        await app.publish(subject="foo.bar", message={"data": 1})

    @app.http.get("/stream")
    async def web_endpoint_listener(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        connection_id = str(uuid.uuid4())[:10]
        await ws.send_str(
            json.dumps({"success": True, "data": "Successfully connected"})
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


# provide parameter for using web_socket - use_web_socket;
client = TestClient(run_panini=run_panini, use_web_socket=True)


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start(sleep_time=3)


def test_wss_bridge():
    print("Before connect")
    client.websocket_session.connect("ws://127.0.0.1:1111/stream")
    print("Connected")
    subscribe_message = {
        "subjects": ["foo.bar"],
        "action": "subscribe",
    }  # subscribe to all subjects with .
    client.websocket_session.send(json.dumps(subscribe_message))
    response = json.loads(client.websocket_session.recv())
    assert response["success"] is True
    assert response["data"] == "Successfully connected"

    response = json.loads(client.websocket_session.recv())
    assert response["data"] == "Successfully connected to events: 'foo.bar'"

    client.publish("start", {})
    response = json.loads(client.websocket_session.recv())["data"]
    assert response["data"] == 1

    unsubscribe_message = {
        "subjects": ["foo.bar"],
        "action": "unsubscribe",
    }  # unsubscribe
    client.websocket_session.send(json.dumps(unsubscribe_message))
    response = json.loads(client.websocket_session.recv())

    assert response["success"] is True
    assert response["data"] == "Successfully unsubscribed from event: foo.bar"

    client.websocket_session.close()
