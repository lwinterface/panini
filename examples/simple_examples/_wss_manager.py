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
                logger.exception(f"WSS error: {str(e)} connection_id {connection_id}")
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
        sub = await self.app.subscribe_new_subject(subject, cb)
        if subject not in self.ssid_map:
            self.ssid_map[subject] = []
        self.ssid_map[subject].append(sub)

    async def unsubscribe(self, client_ws_connection, subject):
        if not subject in self.ssid_map:
            await self.send_to_ws(
                client_ws_connection,
                success=False,
                message=f"The user did not subscribe to event {subject}"
            )
            return
        await self.app.unsubscribe_subject(subject)
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