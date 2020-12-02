from anthill import app as ant_app
import anthill.utils.helper as helper
import anthill.logger.logger_factory as lf
from anthill.logger.logger_factory import Logger

app = ant_app.App(
    service_name='async_publish',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)

processes_queue, stop_event, listener_process = \
        lf.set_logger_in_separate_process(f'/home/danylott/work/opreturn/anthill/anthill/')
log = lf.get_process_logging_config(processes_queue, 'anthill')
log.__class__ = Logger

# log = app.logger.log

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

count_iterations = 50000

@app.task()
async def publish():
    for i in range(count_iterations):
        await app.aio_publish({'data': i}, topic='some.publish.topic')
        log.warning(f'send message {msg}')


# @app.timer_task(interval=2)
# async def publish_pereodically():
#     for _ in range(10):
#         await app.aio_publish(msg, topic='some.publish.topic')
#         log(f'send message from pereodic task {msg}')


@app.listen('some.publish.topic')
async def recieve_messages(topic, message):
    log.warning(f'got message {message}')
    if message['data'] == count_iterations - 1:
        log.warning(f"Time spent: {time.time() - start_time}")

if __name__ == "__main__":
    import time
    start_time = time.time()
    app.start()
    stop_event.set()
    listener_process.join()
