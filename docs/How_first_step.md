1. Make sure that NATS server is running, how to run it here
2. Create simple app might looks like module below

module `app.py`:

```python
from panini import  app as panini_app

app = panini_app.App(
        service_name='quickstart-app',
        host='127.0.0.1',
        port=4222,
)

@app.timer_task(interval=1)
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

It's includes: 

- one timer_task that each second sends message {'some_key':'Hello stream world'}
- one request endpoint - like HTTP endpoints but for

3. Run Panini. Let's 

```python
python3 app.py
```

Check panini app as client of NATS broker:

```python
curl http://127.0.0.1:8222/connz
```

you should get something like:

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
      "cid": 1,
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
      "name": "quickstart-app__c37ddb8038af__556401",
      "lang": "python3",
      "version": "0.9.2"
    }
```

All your microservices under flag `connections`