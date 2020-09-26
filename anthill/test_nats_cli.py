import time
import random
from nats_client.nats_client import NATSClient
from utils.helper import start_thread


#for test
if __name__ == "__main__":

    def msg_generator():
        is_msgs_required = True
        time.sleep(5)
        while True:
            if is_msgs_required:
                n = 0
                for i in range(100):
                    msg = f'some message number {str(n)}'
                    cli.publish(msg, 'topic2.wqe')
                    n += 1
            time.sleep(2)


    def reciever_msg_handler(topic, msg):
        print(f"reciever_msg_handler <<<<< topic: {topic}, msg: {msg}")


    cli = NATSClient(
        client_id='client'+str(random.randint(1,100)),
        host='127.0.0.1',
        port='4222',
        listen_topics_callbacks={'topic2.wqe':reciever_msg_handler},
        # publish_topics=['topic2.wqe',],
        allow_reconnect=True,
        max_reconnect_attempts=10,
        reconnecting_time_wait=1,
    )
    time.sleep(5)
    start_thread(msg_generator)
    import random

    while True:
        b = 1
        for i in range(100000000,10000000000):
            b = b + (i * random.randint(100000000,10000000000))
