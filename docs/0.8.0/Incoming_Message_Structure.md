The **@app.listen** decorator is used to create a listener for messages sent to the specified NATS subject.

```python
@app.listen(subject='some.subject')
async def subject_for_requests_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle incoming message
```

When a message is received, the `msg` object is passed to the callback function. This object contains the following properties:

- **msg.subject** (*str*): The NATS subject that the message was sent from.
- **msg.data** (*dict or str or bytes*): Analogue of the body of an HTTP message.
- **msg.reply** (*str*): A one-time use subject to send a response.
- **msg.sid** (*str*): The subscribe ID that the message was sent from.
- **msg.headers** (*dict*): A dictionary containing any custom headers set externally.