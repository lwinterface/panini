If you would create two microservices that subscribed on subject `some.data.stream.one`, then both will receive all messages

NATS allows easily unite instances of microservice to groups where incoming traffic will equally allocated among microservices of group:

![https://www.notion.so/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F43c9351e-31e0-477f-b31b-baeab4dba35a%2Fpanini_balancer_(1).png?table=block&id=ef5eb0f8-52ea-4466-b1c4-f076672f4050&width=1460&userId=&cache=v2](https://www.notion.so/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F43c9351e-31e0-477f-b31b-baeab4dba35a%2Fpanini_balancer_(1).png?table=block&id=ef5eb0f8-52ea-4466-b1c4-f076672f4050&width=1460&userId=&cache=v2)

Below is code example:

```python

from panini import app as panini_app

app = panini_app.App(
    service_name="async_publish",
    host="127.0.0.1",
    port=4222,
		allocation_queue_group='group1'
)
```

That's it. You only need to specify the group when creating panini app