### How to validate panini microservice is connected
  1. Make sure that NATS server is running, how to run it <here>
2. Create a simple app that periodically sends a message by one asyncio task and receives the message by another task. The whole app is a single module  <span class="red">`app.py`</span>:

```python
from panini import  app as panini_app

app = panini_app.App(
        service_name='quickstart-app',
        host='127.0.0.1',
        port=4222,
)

@app.task(interval=1)
async def publish_periodically():
        await app.publish(subject="some.publish.subject", message={'some_key':'Hello stream world'})

@app.listen("some.request.subject")
async def receive_messages(msg):
    subject = msg.subject
    message = msg.data
		print('Yai! I got new message from stream: {subject}:{message}')

if __name__ == "__main__":
    app.start()
```

3. Run *app.py*:

```python
> python3 app.py
======================================================================================
Panini service connected to NATS..
id: 2
name: quickstart-app__non_docker_env_98846__896705

NATS brokers:
*  nats://127.0.0.1:4222
======================================================================================

Yai! I got new message from stream: {subject}:{message}
Yai! I got new message from stream: {subject}:{message}
Yai! I got new message from stream: {subject}:{message}
Yai! I got new message from stream: {subject}:{message}
```

Check panini app as a client of NATS broker:

```python
curl http://127.0.0.1:8222/connz
```

You should get something like:

```python
{
  "server_id": "NAKBPTP3AFN3XG4CJBMARGTJPWQS6M6DH2OZ4S5F6MAV4DXEJKXNIVC6",
  "now": "2021-05-02T22:36:11.940857451Z",
  "num_connections": 1,
  "total": 1,
  "offset": 0,
  "limit": 1024,
  "connections": [
    {
      "cid": 2,
      "ip": "192.168.240.21",
      "port": 35454,
      "start": "2021-04-27T18:05:31.848989012Z",
      "last_activity": "2021-05-02T22:36:11.882566724Z",
      "rtt": "214µs",
      "uptime": "5d4h30m40s",
      "idle": "0s",
      "pending_bytes": 0,
      "in_msgs": 4,
      "out_msgs": 4,
      "in_bytes": 345,
      "out_bytes": 345,
      "subscriptions": 1,
      "name": "quickstart-app__non_docker_env_98846__896705",
      "lang": "python3",
      "version": "0.9.2"
    }
```

All your microservices under field `connections`
####
Improved text:

### How to Validate Panini Microservice is Connected

To make sure that your Panini microservice is connected to the NATS server, follow these steps:

1. Ensure that the NATS server is running. If you need instructions on how to do this, refer to <here>.
2. Create a simple app to periodically send a message by one asyncio task, and receive the message by another task. This should be a single module named <span class="red">`app.py`</span>, containing the following code:

```python
from panini import  app as panini_app

app = panini_app.App(
        service_name='quickstart-app',
        host='127.0.0.1',
        port=4222,
)

@app.task(interval=1)
async def publish_periodically():
        await app.publish(subject="some.publish.subject", message={'some_key':'Hello stream world'})

@app.listen("some.request.subject")
async def receive_messages(msg):
    subject = msg.subject
    message = msg.data
		print('Yai! I got new message from stream: {subject}:{message}')

if __name__ == "__main__":
    app.start()
```

3. Run *app.py*:

```python
> python3 app.py
```

This should give you an output like:

```python
======================================================================================
Panini service connected to NATS..
id: 2
name: quickstart-app__non_docker_env_98846__896705

NATS brokers:
*  nats://127.0.0.1:4222
======================================================================================

Yai! I got new message from stream: {subject}:{message}
Yai! I got new message from stream: {subject}:{message}
Yai! I got new message from stream: {subject}:{message}
Yai! I got new message from stream: {subject}:{message}
```

To check if the Panini app is connected to the NATS broker, run the following command in your terminal:

```python
curl http://127.0.0.1:8222/connz
```

You should get an output like this:

```python
{
  "server_id": "NAKBPTP3AFN3XG4CJBMARGTJPWQS6M6DH2OZ4S5F6MAV4DXEJKXNIVC6",
  "now": "2021-05-02T22:36:11.940857451Z",
  "num_connections": 1,
  "total": 1,
  "offset": 0,
  "limit": 1024,
  "connections": [
    {
      "cid": 2,
      "ip": "192.168.240.21",
      "port": 35454,
      "start": "2021-04-27T18:05:31.848989012Z",
      "last_activity": "2021-05-02T22:36:11.882566724Z",
      "rtt": "214µs",
      "uptime": "5d4h30m40s",
      "idle": "0s",
      "pending_bytes": 0,
      "in_msgs": 4,
      "out_msgs": 4,
      "in_bytes": 345,
      "out_bytes": 345,
      "subscriptions": 1,
      "name": "quickstart-app__non_docker_env_98846__896705",
      "lang": "python3",
      "version": "0.9.2"
    }
```

All your microservices should be listed under the `connections` field.