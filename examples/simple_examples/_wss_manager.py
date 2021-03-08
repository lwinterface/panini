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
