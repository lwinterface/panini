Panini also use [aiohttp] ([https://github.com/aio-libs/aiohttp](https://github.com/aio-libs/aiohttp)) for websockets. Let's see how it works using the example below.

Suppose we want to create a microservice that will subscribe to the desired NATS subject and broadcast them to a website in a browser in live mode using websockets. To implement this we need:

- Web interface with web socket connection
- GET endpoint to upload interface
- POST endpoint to subscribe/unsubscribe to NATS subjects
- WSS endpoint to receive live messages
- Some message generator to test microservice
- Main logic that's handle subscribe/unsubscribe requests

<написать где взял интерфейс>

Let's split app into two modules. One for main app - `main.py` and another for subscribe/unsubscribe request handler & web page - `handler.py` 

main.py:

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
    web_server=True,
    web_port=11111,
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
		"""WebSocket connection """
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
		"""
		app calls it for each new message from
		NATS and redirects the message
		"""
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
```

handler.py:

```python
import json
from panini.utils.logger import get_logger

log = get_logger(None)

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
            var ws = new WebSocket(`ws://${window.location.hostname}:1111/stream`);
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
                body = json.loads(msg.data)
                action = body["action"] if "action" in body else "subscribe"
                if action not in ["subscribe", "unsubscribe"]:
                    await client_ws_connection.send_str(
                        json.dumps(
                            {
                                "success": False,
                                "data": "The user has to specify action in message ('subscribe' or 'unsubscribe')",
                            }
                        )
                    )
                if "subjects" not in body:
                    raise Exception("subjects required")
                subjects = body["subjects"]
                if action == "subscribe":
                    for subject in subjects:
                        cb = await self._get_callback(client_ws_connection)
                        ssid = await self.app.aio_subscribe_new_subject(subject, cb)
                        if subject not in self.ssid_map:
                            self.ssid_map[subject] = []
                        self.ssid_map[subject].append(ssid)
                    await client_ws_connection.send_str(
                        json.dumps(
                            {
                                "success": True,
                                "data": f"Successfully connected to events: {str(subjects)[1:-1]}",
                            }
                        )
                    )
                elif action == "unsubscribe":
                    for subject in subjects:
                        if subject in self.ssid_map:
                            for ssid in self.ssid_map[subject]:
                                await self.app.aio_unsubscribe_ssid(ssid)
                            await client_ws_connection.send_str(
                                json.dumps(
                                    {
                                        "success": True,
                                        "data": f"Successfully unsubscribed from event: {subject}",
                                    }
                                )
                            )
                        else:
                            await client_ws_connection.send_str(
                                json.dumps(
                                    {
                                        "success": False,
                                        "data": f"The user did not subscribe to event {subject}",
                                    }
                                )
                            )
            except Exception as e:
                log.error(f"WSS error: {str(e)} connection_id {connection_id}")
                try:
                    await client_ws_connection.send_str(
                        json.dumps({"success": False, "error": str(e)})
                    )
                except Exception as e:
                    log.error(str(e), level="error")
                return client_ws_connection

    async def _get_callback(self, subscriber):
        if hasattr(self, "callback"):
            cb = self.callback
        else:
            raise Exception("self.callback function for incoming messages expected")

        async def wrapper(msg):
            return await cb(subscriber, msg)
        return wrapper
```

That's it! Les't run our [main.py](http://main.py) and check [http://127.0.0.1:11111](http://127.0.0.1:11111) , if everything correct you have to got this page:

![https://www.notion.so/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F7a4f5637-0c4c-4423-af15-b16170e97399%2FScreenshot_2021-04-29_at_19.18.29.png?table=block&id=0c3302e4-3b32-4cb8-a92e-858ddaa67695&width=2560&userId=&cache=v2](https://www.notion.so/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F7a4f5637-0c4c-4423-af15-b16170e97399%2FScreenshot_2021-04-29_at_19.18.29.png?table=block&id=0c3302e4-3b32-4cb8-a92e-858ddaa67695&width=2560&userId=&cache=v2)

You can also check app below in our example [here](https://github.com/lwinterface/panini/blob/master/examples/simple_examples/async_wss_web_server.py)