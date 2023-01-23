### Decorators

<span class="red">`@app.task()`</span> - an asyncio task that is launched with the application, executed once

Usage example:

```python
@app.task()
async def publish():
    while True:
        message = get_some_update()
        await app.publish(subject='some.subject', message=message)
```

<span class="red">`@app.task(interval=1)`</span> - same asyncio task but runs at a given interval

Usage example:

```python
@app.task(interval=2)
async def your_periodic_task():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message={'some':'data'})
```

Supported arguments:

- **interval**(*int or float*): waiting time between periodic task executions

<span class="red">`@app.listen(subject="some.subject")`</span> - subscribe to the specified subject and run a callback for every incoming message

Usage example:

```python
@app.listen(subject='some.subject')
async def subject_for_requests_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle incoming message
```

Supported arguments:

- **subject**(*str*): NATS subject to subscribe

### Functions

Parameters from all functions:

- **subject**(*str*): NATS subject to send or subscribe
- **msg**(*<class 'Msg'>*): NATS single message object to receive
- **reply_to**(*str*): An additional subject for a response, relevant if you want to request from one microservice but receive by another one
- **force**(*bool*): This flag trigger immediately sends all messages in a buffer. Otherwise, the messages are send periodically. Sending frequency depends on how many asyncio tasks are running in the loop
- **data_type**(*<class 'type'> or str*): allows choosing a type of message body to send or receive. More details <here>
- **timeout**(*int or float*): only for requests, like HTTP request timeout but for NATS requests
- **ssid**(*str*): subscription ID
- **callback**(*CoroutineType*): function to call when received a new message

<span class="dkGreen">app.publish</span>

Usage example:

```python
await app.publish(subject='some.subject', message={'some':'message'})
```

Supported parameters:

- **subject**
- **message**
- **reply_to**
- **force**

response - None

<span class="dkGreen">app.request</span>

Usage example:

```python
response = await app.request(subject='some.subject', message={'some':'message'})
```

Supported parameters:

- **subject**
- **message**
- **timeout**
- **response_data_type**

response - message body, type depends on given data_type

<span class="dkGreen">app.nats.publish_from_another_thread</span>

Usage example:

```python
app.nats.publish_from_another_thread(subject='some.subject', message={'some':'message'})
```

Supported arguments:

- **subject**
- **message**
- **reply_to**
- **force**

response - None

<span class="dkGreen">app.request_from_another_thread</span>

Usage example:

```python
response = await app.request_from_another_thread(subject='some.subject', message={'some':'message'})
```

Supported parameters:

- **subject**
- **message**
- **timeout**
- **headers**

response - message body, type depends on given data_type

<span class="dkGreen">app.subscribe_new_subject</span>

Usage example:

```python
await app.subscribe_new_subject(subject='some.subject', callback=some_funcion)
```

Supported arguments:

- **subject**
- **callback**

response - subscription ID

<span class="dkGreen">app.unsubscribe_subject</span>

Usage example:

```python
await app.unsubscribe_subject(subject='some.subject')
```

Supported arguments:

- **subject**

response - None

<span class="dkGreen">app.unsubscribe_ssid</span>

Usage example:

```python
await app.unsubscribe_ssid(ssid='some.subject')
```

Supported arguments:

- **ssid**

response - None

<span class="dkGreen">app.disconnect</span>

Usage example:

```python
await app.disconnect()
```

<span class="dkGreen">app.publish_sync</span>

Usage example:

```python
app.publish_synс(subject='some.subject', message={'some':'message'})
```

Supported parameters:

- **subject**
- **message**
- **reply_to**
- **force**

response - None

<span class="dkGreen">app.request_sync</span>

Usage example:

```python
await app.request_sync(subject='some.subject', message={'some':'message'})
```

Supported parameters:

- **subject**
- **message**
- **timeout**
- **response_data_type**

response - message body, type depends on given response_data_type

<span class="dkGreen">app.subscribe_new_subject_sync</span>

Usage example:

```python
await app.subscribe_new_subject(subject='some.subject', callback=some_funcion)
```

Supported arguments:

- **subject**
- **callback**

response - subscription ID

<span class="dkGreen">app.unsubscribe_subject_sync</span>

Usage example:

```python
await app.unsubscribe_subject(subject='some.subject')
```

Supported arguments:

- **subject**

response - None

<span class="dkGreen">app.disconnect_sync</span>

Usage example:

```python
app.disconnect_sync()
```

app.middlewares

Usage example:

```python
app.add_middleware(SomeMiddleware)
```

Supported arguments:

- cls(*class 'Middleware'*)