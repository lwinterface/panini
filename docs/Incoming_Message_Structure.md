Usage example:

```python
@app.listen(subject='some.subject')
async def subject_for_requests_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle incoming message
```

**msg.subject**(*str*) - NATS subject that message comes from

**msg.data**(*dict or str or bytes*) - analogue of HTTP message's body

**msg.reply**(*str*) - one-time use subject to send a response

**msg.sid**(*str*) - subscribe ID that message comes from

**msg.context**(*dict*) - any custom dict for internal use