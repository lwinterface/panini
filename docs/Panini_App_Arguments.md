Panini app available on <span class="red">`panini.app.App`</span>

Usage example:

```python
from panini import app as panini_app

app = panini_app.App(
        service_name='listener_app',
        host='127.0.0.1',
        port=4222,
)
```

Parameters:

- **host**(*str*): NATS broker host
- **port**(*int*): NATS broker port
- **service_name**(*str*): Name of microservice, will be the part of NATS client_id if you didn't set custom client_id
- **servers**(*list*): Alternative to NATS broker host+NATS broker port. Allows microservice to establish a connection to multiple NATS brokers
- **client_id**(*str*): Custom NATS client_id
- **reconnect**(*bool*): Connects again if a lost connection to NATS broker
- **max_reconnect_attempts**(*int*): Number of attempts to reconnect
- **reconnecting_time_sleep**(*int*): Pause between reconnections
- **allocation_queue_group**(*str*): Name of the queue group. Incoming traffic allocates between group members.
- **logger_required**(*bool*): Logger required for the project, if not - default logger will be provided
- **logger_files_path**(*str*): Main path for logs
- **logger_in_separate_process**(*bool*): Use log in the same or in different process
- **pending_bytes_limit**(*int*): Limit of bytes for a single incoming message
- **auth**(*dict*): Dict with arguments for authentication