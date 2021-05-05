### Decorators

@app.task() - an asyncio task that is launched with the application, executed once

usage example:

```python
@app.task()
async def publish():
    while True:
        message = get_some_update()
        await app.publish(subject='some.subject', message=message)
```

supported arguments

@app.timer_task(interval=1) - asyncio task that will run at a given interval

usage example:

```python
@app.timer_task(interval=2)
async def your_periodic_task():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message={'some':'data'})
```

@app.listen("some.subject") - subscribe to the specified subject and run a callback for every incoming message

usage example:

```python
@app.listen('some.subject')
async def subject_for_requests_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle incoming message
```

### Functions

general argument defenitions

- subject: NATS subject to send or subscribe
- message: NATS single message body to send or receive
- reply_to: additional subject for response, relevant if you want to request from one microservice but receive by another one
- force: this flag trigger immediate send all messages in buffer, otherwise it send periodically. Sending frequency depends on how many asyncio tasks running in loop
- data_type: allows to chose type of message body to send or receive, supports `json.dumps`(default for sending messages), `json.loads`(default for received messages), `str`, `bytes`. More detailed here
- timeout: only for requests, equal to http request timeout
- ssid: subscription ID

app.publish

usage example

```python
await app.publish(subject='some.subject', message={'some':'message'})
```

supported arguments:

- subject
- message
- reply_to
- force
- data_type

response - None

app.request

```python
response = await app.reqeust(subject='some.subject', message={'some':'message'})
```

supported arguments:

- subject
- message
- timeout
- data_type

response - message body, type depends on given data_type

app.publish_from_another_thread

```python
app.publish_from_another_thread(subject='some.subject', message={'some':'message'})
```

supported arguments:

- subject
- message
- reply_to
- force
- data_type

response - None

app.request_from_another_thread

```python
response = await app.request_from_another_thread(subject='some.subject', message={'some':'message'})
```

supported arguments:

- subject
- message
- timeout
- data_type

response - message body, type depends on given data_type

app.subscribe_subject

```python
await app.subscribe_subject(subject='some.subject', callback=some_funcion)
```

supported arguments:

- subject
- callback

response - subscription ID

app.unsubscribe_subject

```python
await app.unsubscribe_subject(subject='some.subject')
```

supported arguments:

- subject

response - None

app.unsubscribe_ssid

```python
await app.unsubscribe_ssid(ssid='some.subject')
```

supported arguments:

- ssid

response - None

#TODO: app.publish_sync

#TODO: app.request_sync

#TODO: app.request_from_another_thread_sync

#TODO: app.publish_from_another_thread_sync

#TODO: app.subscribe_subject_sync

#TODO: app.unsubscribe_subject_sync

#TODO: app.disconnect

#TODO: middlewares