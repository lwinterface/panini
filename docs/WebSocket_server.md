Panini also uses [Aiohttp](https://github.com/aio-libs/aiohttp) for WebSockets. Let's see how it works using the example below.

Suppose we want to create a microservice - a gateway between NATS stream and WebSockets stream. It subscribes to the desired NATS subject from a frontend and broadcasts them to a frontend in "live mode". To implement this we need:

- Web interface with web socket connection
- GET endpoint to upload interface
- POST endpoint to subscribe/unsubscribe to NATS subjects
- WSS endpoint to receive live messages
- Some NATS message producer to test microservice
- Main logic that handles subscribe/unsubscribe requests

Let's split the app into two modules. One for the main app - <span class="red">`main.py`</span> and another for subscribe/unsubscribe request handler & web page - <span class="red">`handler.py` </span>

<span class="red">`main.py`</span>:

```python
import uuid
import random
import json
from aiohttp import web
from panini import app as panini_app
from handler import WSSManager, html

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
```

1. <span class="red">`from handler import WSSManager, html`</span> imports from another module, handler.py
2. <span class="red">`manager = WSSManager(app)`</span>  initializing of class that handles subscription/unsubscription requests from the users of the frontend
3. <span class="red">`manager.callback = incoming_messages_callback`</span>  setting callback to incoming NATS messages
4. <span class="red">`test_msg`</span>  - message for NATS stream
5. <span class="red">`@app.task(interval=1)`</span>  - function under the decorator publishes messages periodically to subject "test.subject"
6. <span class="red">`@app.http.get("/")`</span>  - function under the decorator received HTTP request to get main web page
7. <span class="red">`@app.http.get("/stream")`</span>  - function under the decorator received HTTP request to subscribe user to NATS subject
8. <span class="red">`app.http_server.web_app["subscribers"] = {}`</span>  - This is where we store subscribers

Let's take a look at handler.py. It includes web page and WebSocket handler

<span class="red">`handler.py`:

```python
import json
import copy
from panini.utils.logger import get_logger
from aiohttp.http_websocket import WSMsgType

logger = get_logger(None)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>NATS Bridge</title>
    </head>
    <body>
        <h1>WebSocket</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket(`ws://${window.location.hostname}:5001/stream`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

class WSSManager:
    ssid_map = {}

    def __init__(self, app):
        self.app = app

    async def client_listener(self, client_ws_connection, connection_id):
        """app calls it for each WSS message from user"""
        while True:
            try:
                msg = await client_ws_connection.receive()
                if self.is_close_connection_message(msg):
                    await self.close_ws_client(client_ws_connection, connection_id)
                    return client_ws_connection
                body = json.loads(msg.data)
                action = self.get_action(body)
                await self.validate_ws_message(client_ws_connection, body, action)
                subjects = body["subjects"]
                if action == "subscribe":
                    for subject in subjects:
                        cb = await self.get_callback(client_ws_connection)
                        await self.subscribe(subject, cb)
                    await self.send_to_ws(
                        client_ws_connection,
                        success=True,
                        message=f"Successfully connected to events: {str(subjects)[1:-1]}"
                    )
                elif action == "unsubscribe":
                    for subject in subjects:
                        await self.unsubscribe(client_ws_connection, subject)
            except Exception as e:
                logger.error(f"WSS error: {str(e)} connection_id {connection_id}")
                try:
                    await self.send_to_ws(
                        client_ws_connection,
                        success=False,
                        message=str(e)
                    )
                except Exception as e:
                    logger.error(str(e), level="error")
                return client_ws_connection

    async def validate_ws_message(self, client_ws_connection, body, action):
        if action not in ["subscribe", "unsubscribe"]:
            message = f"The user has to specify action in message ('subscribe' or 'unsubscribe'), got {action} instead"
            await self.send_to_ws(
                client_ws_connection,
                success=False,
                message=message
            )
            raise Exception(message)
        if "subjects" not in body:
            raise Exception("subjects required")

    def is_close_connection_message(self, msg):
        if msg.type == WSMsgType.CLOSE and msg.data in range(1000,1003):
            return True

    async def close_ws_client(self, client_ws_connection, conn_id):
        connections = copy.copy(self.ssid_map)
        for subject in connections:
            if conn_id in self.ssid_map[subject]:
                try:
                    del self.ssid_map[subject][conn_id]
                    if self.ssid_map[subject] == {}:
                        await self.app.unsubscribe_subject(subject)
                        del self.ssid_map[subject]
                except Exception as e:
                    logger.error(str(e))
        await client_ws_connection.close()

    def get_action(self, body):
        return body["action"] if "action" in body else "subscribe"

    async def send_to_ws(self, client_ws_connection, success: bool, message: str):
        message = json.dumps({
            'success': success,
            'message': message,
        })
        await client_ws_connection.send_str(message)

    async def subscribe(self, subject, cb):
        ssid = await self.app.subscribe_new_subject(subject, cb)
        if subject not in self.ssid_map:
            self.ssid_map[subject] = []
        self.ssid_map[subject].append(ssid)

    async def unsubscribe(self, client_ws_connection, subject):
        if not subject in self.ssid_map:
            await self.send_to_ws(
                client_ws_connection,
                success=False,
                message=f"The user did not subscribe to event {subject}"
            )
            return
        for ssid in self.ssid_map[subject]:
            await self.app.unsubscribe_ssid(ssid)
        await self.send_to_ws(
            client_ws_connection,
            success=True,
            message=f"Successfully unsubscribed from event: {subject}"
        )

    async def get_callback(self, subscriber):
            if hasattr(self, "callback"):
                cb = self.callback
            else:
                raise Exception("self.callback function for incoming messages expected")

            async def wrapper(msg):
                return await cb(subscriber, msg)
            return wrapper
```

1. <span class="red">`html`</span> - web page html/js code
2. <span class="red">`WSSManager`</span> - manage every WebSocket request with NATS subject

That's it! Let's run our [main.py](http://main.py) and check [http://127.0.0.1:](http://127.0.0.1:11111)5001:

```python
> python3 main.p
======================================================================================
Panini service connected to NATS..
id: 5
name: async_NATS_WSS_bridge__non_docker_env_486358__955463

NATS brokers:
*  nats://127.0.0.1:4222
======================================================================================

======== Running on http://0.0.0.0:5001 ========
```

Then you need to follow the link [http://0.0.0.0:5001](http://0.0.0.0:5001/) . If everything is correct you will get this page:

![https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F7a4f5637-0c4c-4423-af15-b16170e97399%2FScreenshot_2021-04-29_at_19.18.29.png?table=block&id=86dcd6a6-0a20-49b7-9e65-eb51c7290425&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=2000&userId=&cache=v2](https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F7a4f5637-0c4c-4423-af15-b16170e97399%2FScreenshot_2021-04-29_at_19.18.29.png?table=block&id=86dcd6a6-0a20-49b7-9e65-eb51c7290425&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=2000&userId=&cache=v2)

In order to subscribe to NATS subject "test.subject" you need to send a request in expected format:

{"subjects":["test.subject"],"action":"subscribe"}

If everything is correct you should see NATS message on the web page:

![Screenshot 2021-11-03 at 14.36.40.png](https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2Faf0d2eb8-415d-4092-85c1-d7ba77b17251%2FScreenshot_2021-11-03_at_14.36.40.png?table=block&id=cda42be4-4068-42f0-be53-c0e1fcd53664&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=2000&userId=&cache=v2)

You can also check this app below in our example [here](https://github.com/lwinterface/panini/blob/master/examples/simple_examples/async_wss_web_server.py).