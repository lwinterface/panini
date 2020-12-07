from anthill import app as ant_app

app = ant_app.App(
    service_name='async_publish',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)

log = app.logger.log

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

@app.task()
async def publish():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')
        log(f'send message {msg}')


@app.timer_task(interval=1)
async def publish_pereodically():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')
        log(f'send message from pereodic task {msg}')


@app.listen('some.publish.topic')
async def recieve_messages(topic, message):
    log(f'got message {message}')

if __name__ == "__main__":
    app.start()
