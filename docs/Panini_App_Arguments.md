The Panini app is available on <span class="red">`panini.app.App`</span>. An example of how to use it is provided below:

```python
from panini import app as panini_app

app = panini_app.App(
        service_name='listener_app',
        host='127.0.0.1',
        port=4222,
)
```

The following parameters can be used optionaly when creating an instance of the Panini app:

- **host**(*str*): The host of the NATS broker.
- **port**(*int*): The port of the NATS broker.
- **service_name**(*str*): The name of the microservice, which will be used as part of the NATS client_id if a custom client_id is not set.
- **servers**(*list*): An alternative to the NATS broker host and port, allowing the microservice to establish a connection with multiple NATS brokers.
- **client_id**(*str*): A custom NATS client_id.
- **reconnect**(*bool*): Establishes a connection again if the connection to the NATS broker is lost.
- **max_reconnect_attempts**(*int*): The maximum number of attempts to reconnect.
- **reconnecting_time_sleep**(*int*): The pause between reconnections.
- **allocation_queue_group**(*str*): The name of the queue group. Incoming traffic is allocated between group members.
- **logger_required**(*bool*): Logger required for the project; if not, a default logger will be provided.
- **logger_files_path**(*str*): The main path for logs.
- **logger_in_separate_process**(*bool*): Use log in the same or in different process.
- **pending_bytes_limit**(*int*): The limit of bytes for a single incoming message.
- **auth**(*dict*): A dict with arguments for authentication.
- Any additional arguments from [nats.py Client class](https://github.com/nats-io/nats.py/blob/0c244c857a15a2af98b3611af795fc2ebc52b2e4/nats/aio/client.py#L275).

When creating an instance of the Panini app, make sure to provide the necessary parameters in order to ensure successful connection.