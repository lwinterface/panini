Sometimes there can be too much traffic and it is necessary to scale services horizontally, i. e. create several instances of a microservice in order to distribute the incoming traffic between them. This section will describe how to work with this issue.

Let's say you created two instances of a microservice that are subscribed on the subject <span class="red">`some.data.stream.one`</span>, then both will receive all messages. It's the default behaviour of NATS microservices. NATS allows for easily uniting instances of a microservice to a group where incoming traffic will be equally allocated among instances automatically:

![https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F43c9351e-31e0-477f-b31b-baeab4dba35a%2Fpanini_balancer_(1).png?table=block&id=6e784580-726a-4500-b4e0-a30c70104a43&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=1460&userId=&cache=v2](https://twilight-chord-83a.notion.site/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F43c9351e-31e0-477f-b31b-baeab4dba35a%2Fpanini_balancer_(1).png?table=block&id=6e784580-726a-4500-b4e0-a30c70104a43&spaceId=ad8a90bf-1524-4f67-980e-074c3aba664d&width=1460&userId=&cache=v2)

How to program traffic distribution with Panini:

```python

from panini import app as panini_app

app = panini_app.App(
    service_name="async_publish",
    host="127.0.0.1",
    port=4222,
		allocation_queue_group='unit1'
)
```

When the class App is initialized, it takes <span class="red">`allocation_queue_group`</span> as an additional argument. Then all microservices in this group <span class="red">`unit1`</span> will distribute the incoming traffic among the group members.

That's it. You only need to specify the group when creating a Panini app.