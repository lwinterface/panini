from aiohttp import web
from anthill import app as ant_app
import time
import json
import threading
import uvicorn
import contextlib
from fastapi import WebSocket
from anthill.utils.helper import start_thread
from fastapi.responses import HTMLResponse

print('STAAART')
app = ant_app.App(
    service_name='async_web_server_fastapi',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
    web_server=True,
    web_framework='fastapi',
    web_port=5000,
)

log = app.logger.log

html = """
<!DOCTYPE html>
<html>
    <head>  
        <title>Websocket-NATS bridge</title>
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
            var ws = new WebSocket("ws://localhost:5000/ws");
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

msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}

subscribers = []

@app.task()
async def publish():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')

@app.timer_task(interval=2)
async def publish_pereodically():
    await app.aio_publish(msg, topic='some.publish.topic')

@app.listen('some.publish.topic')
async def topic_for_requests_listener(topic, message):
    log(f'got message {message}')
    for ws in subscribers:
        try:
            await ws.send_text(json.dumps({'topic':topic, 'message':message}))
        except Exception as e:
            log(f'error: {str(e)}')

app_http = app.http

@app_http.get("/")
async def get():
    return HTMLResponse(html)


@app_http.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global subscribers
    subscribers.append(websocket)
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")






# config = uvicorn.Config("async_fastapi_server:app.http", host="127.0.0.1", port=5000, log_level="info")
# server = Server(config=config)


if __name__ == "__main__":
    print('__name__ == "__main__"')
    app.start(uvicorn_app_target="async_fastapi_server:app_http")
