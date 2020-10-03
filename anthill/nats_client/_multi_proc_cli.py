import sys, os
import json
import uuid
import time
import random
import asyncio
import datetime
import multiprocessing
from itertools import cycle
from queue import Empty
from nats.aio.client import Client as NATS
from ..logger.logger import Logger, InterServicesRequestLogger
from ..utils.helper import start_thread, start_process, is_json
from ._redis_response import RedisResponse, RedisQueue
from ..exceptions import EventHandlingError, PublishError

log = Logger(name='_MessengerClient_V3').log
# isr_log = InterServicesRequestLogger(name='InterServicesRequest_V3', separated_file=True).isr_log
isr_log = Logger(name='InterServicesRequest_V3', log_file=f'InterServicesRequest_V3.log').log

LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC = os.environ['CLIENT_ID'] if 'CLIENT_ID' in os.environ else str(uuid.uuid4())[10:] + '__new_subscribtion'


def transform_topic(topic, keyword=''):
    return ".".join([os.environ['CLIENT_ID'], topic.split('.')[-1], keyword])


class _MultiProcNATSClient(object):
    """
    Subinterface for NATSClient, create additional processes for sending and listening
    """

    def __init__(self, child_obj):
        #TODO: check that all cls attr exists
        self.__dict__ = child_obj.__dict__
        self.listen_message_queue = {}
        # [self.listen_message_queue.update({topic: multiprocessing.Queue()}) for topic in self.listen_topics_callbacks]
        [self.listen_message_queue.update({topic: RedisQueue(transform_topic(topic, 'listener'))}) for topic in self.listen_topics_callbacks]
        self.publish_message_queue = {}
        # [self.publish_message_queue.update({transform_topic(topic): RedisResponse(transform_topic(topic))}, host=self.redis_host, port=self.redis_port) for topic in
        #  self.publish_topics]
        # [self.publish_message_queue.update({transform_topic(topic): RedisResponse(transform_topic(topic))},
        #                                    host=self.redis_host, port=self.redis_port) for topic in
        #  self.publish_topics]
        [self.publish_message_queue.update({transform_topic('queue'+str(i)): RedisResponse(transform_topic('queue'+str(i)), 'publisher')}) for i in range(self.num_of_queues)]
        self.publish_queue_circle = cycle(list(self.publish_message_queue.values()))
        self.new_listen_topics_redis_queue = RedisQueue(transform_topic(LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC))
        self.forced_closure = False
        self._launch()

    def _launch(self):
        self._launch_listener()
        self._launch_sender()
        for topic, q in self.listen_message_queue.items():
            print(f'{os.environ["CLIENT_ID"]}*listening for topic: {topic}')
            start_thread(self._listen_incoming_messages_forever, args=(q, topic))

    async def aio_subcribe_new_topic(self, topic, callback):
        subcribe_new_topic(topic, callback)

    def listen_new_topic(self, topic, callback):
        # TODO: include all "topic_include" rules
        q = RedisQueue(topic)
        self.listen_message_queue.update({topic: q})
        self.new_listen_topics_redis_queue.put(topic)
        print(f'{os.environ["CLIENT_ID"]}*listening for topic: {topic}')
        start_thread(self._listen_incoming_messages_forever, args=(q, topic))

    def _launch_listener(self):
        listen_queue_topics = list(self.listen_message_queue.keys())
        start_process(_ListenerProc, kwargs={
            'client_id':self.client_id,
            'host':self.host,
            'port':self.port,
            'listen_queue_topics':listen_queue_topics,
            'allow_reconnect':self.allow_reconnect,
            'max_reconnect_attempts':self.max_reconnect_attempts,
            'reconnecting_time_wait':self.reconnecting_time_wait
        })

    def _launch_sender(self):
        publish_queue_topics = list(self.publish_message_queue.keys())
        start_process(_SenderProc, kwargs={
            'client_id': self.client_id,
            'host': self.host,
            'port': self.port,
            'publish_queue_topics': publish_queue_topics,
            'allow_reconnect': self.allow_reconnect,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'reconnecting_time_wait': self.reconnecting_time_wait,
        })

    def _listen_incoming_messages_forever(self, shared_queue, topic):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print(f'_listen_incoming_messages_forever: {shared_queue.key}')
        while self.forced_closure is False:
            try:
                new_msg = shared_queue.get(block=False)
                if new_msg is None:
                    continue
                base_topic = new_msg.pop('base_topic')
                if 'reply' in new_msg:
                    reply_key = new_msg.pop('reply')
                    # isr_log(f"3RECIEVED REQUEST msg: {new_msg['message']}, {base_topic}")
                callbacks = self.listen_topics_callbacks[base_topic]
                for callback in callbacks:
                    reply = callback(**new_msg)
                    if reply:
                        if not 'reply_key' in locals():
                            isr_log(f"Got reply from callback but NATS massage doesn't expect for it. \ntopic: {base_topic}, message: {new_msg}, reply: {reply}", level='error', slack=True)
                        else:
                            if type(reply) is dict:
                                reply = json.dumps(reply)
                            else:
                                reply = str(reply)
                            isr_log(f"4SENDING RESPONSE msg: {new_msg['message']} {base_topic}")
                            RedisResponse(reply_key).put(str(reply))
            except Empty:
                pass
            except Exception as e:
                if not 'reply' in locals():
                    reply = "hasn't handeled"
                if not 'new_msg' in locals():
                    new_msg = "hasn't handeled"
                error = f"incoming message handling error {str(e)}, reply: {reply}, new_msg type: {type(new_msg)} new_msg: {new_msg}"
                log(error, level='error', slack=True)

    def _listen_incoming_messages_forever_old(self, shared_queue, topic):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while self.forced_closure is False:
            try:
                new_msg = shared_queue.get(timeout=5)
                base_topic = new_msg.pop('base_topic')
                if 'reply' in new_msg:
                    reply_key = new_msg.pop('reply')
                    # isr_log(f"3RECIEVED REQUEST msg: {new_msg['message']}, {base_topic}")
                callbacks = self.listen_topics_callbacks[base_topic]
                for callback in callbacks:
                    reply = callback(**new_msg)
                    if reply:
                        if not 'reply_key' in locals():
                            isr_log(f"Got reply from callback but NATS massage doesn't expect for it. \ntopic: {base_topic}, message: {new_msg}, reply: {reply}", level='error', slack=True)
                        else:
                            if type(reply) is dict:
                                reply = json.dumps(reply)
                            else:
                                reply = str(reply)
                            isr_log(f"4SENDING RESPONSE msg: {new_msg['message']} {base_topic}")
                            RedisResponse(reply_key).put(str(reply))
            except Empty:
                pass
            except EventHandlingError as e:
                if not 'reply' in locals():
                    reply = "hasn't handeled"
                if not 'new_msg' in locals():
                    new_msg = "hasn't handeled"
                error = f"incoming message handling error {str(e)}, reply: {reply}, new_msg type: {type(new_msg)} new_msg: {new_msg}"
                log(error, level='error', slack=True)

    def publish(self, message, topic, reply_to=None):
        if reply_to:
            raise NotImplementedError
        if type(message) == str and is_json(message):
            message = json.loads(message)
        message['topic'] = topic
        message = json.dumps(message)
        q = self.publish_queue_circle.__next__()
        q.put(message)

    def publish_request(self, message, topic, timeout=10, unpack=True):
        try:
            reply = str(uuid.uuid4())[10:]
            redis_response = RedisResponse(reply)
            if type(message) == dict:
                message['reply'] = reply
                message['timeout'] = timeout
            elif type(message) == str and is_json(message):
                message = json.loads(message)
                message['reply'] = reply
                message['timeout'] = timeout
            # isr_log(f'1BRREQUEST reply {reply} timeout {timeout}', phase='request', topic=topic, redis_topic=transform_topic(topic))
            self.publish(message, topic)
            response = redis_response.return_response_when_appeared(topic=None, timeout=timeout)
            # isr_log(f'6ARREQUEST reply {reply}', phase='response', topic=topic)
            if unpack:
                return json.loads(response.data.decode())
            return response.data.decode()
        except Exception as e:
            isr_log(f"6ERROR reply {reply} "+str(e), level='error', from_='PublishClientInterface.publish_request', topic=topic, request=str(message))

    def publish_request_reply_to_another_topic(self, message, topic, reply_to=None):
        raise NotImplementedError

    async def aio_publish(self, message, topic, reply_to=None, force=None):
        self.publish(message, topic)

    async def aio_publish_request(self, message, topic, timeout=10, unpack=True):
        return self.publish_request(message, topic, timeout=timeout, unpack=unpack)

    async def aio_publish_request_with_reply_to_another_topic(self, message, topic, reply_to=None):
        raise NotImplementedError

    def close(self):
        self.close()

class _ListenerProc():
    def __init__(self,
              client_id: str,
              host: str,
              port: int,
              listen_queue_topics: list,
              allow_reconnect: bool,
              max_reconnect_attempts: int,
              reconnecting_time_wait: int):
        self.role = 'listener'
        self.listen_queue_topics = listen_queue_topics
        self.loop = asyncio.get_event_loop()
        self.client = NATS()
        self.loop.run_until_complete(self.client.connect(host+':'+port, loop=self.loop, name=client_id + '__' + self.role))
        self.connected = True
        log('connected ' + self.role)
        self.loop.run_until_complete(self.subscribe_all())
        self.loop.create_task(self.listen_for_new_subscribtion(LISTEN_FOR_NEW_SUBSCRIPTION_TOPIC))
        self.loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(self.loop)))

    async def subscribe_all(self):
        if self.connected:
            for topic in self.listen_queue_topics:
                await self.subscribe(topic)

    async def subscribe(self, topic):
        wrapped_callback = self.wrap_callback(topic, RedisQueue(transform_topic(topic, self.role)), self.client)
        await self.client.subscribe(topic, cb=wrapped_callback, pending_bytes_limit=65536 * 1024 * 10)

    async def listen_for_new_subscribtion(self, topic):
        try:
            new_subscribtion_queue = RedisResponse(topic)
            while True:
                if new_subscribtion_queue.empty() is True:
                    await asyncio.sleep(0.1)
                    continue
                new_topic_raw = new_subscribtion_queue.get()
                new_topic = new_topic_raw.decode()
                await self.subscribe(new_topic)
        except Exception as e:
            log(f"_handle_topic_queue_forever error {os.environ['SERVICE_NAME']}: " + str(e), level='error')

    def wrap_callback(self, base_topic, q, cli):
        async def wrapped_callback(msg):
            subject = msg.subject
            reply = msg.reply
            data = msg.data.decode()
            print(f'lc {q.key}')
            if reply == "":
                q.put(json.dumps(dict(base_topic=base_topic, topic=subject, message=data)))
            else:
                q.put(json.dumps(dict(base_topic=base_topic, topic=subject, message=data, reply=reply)))
                redis_response = RedisResponse(reply)
                response = redis_response.return_response_when_appeared(topic=base_topic)
                try:
                    await cli.publish(reply, response.data)
                except Exception as e:
                    isr_log(f'ERROR: {str(e)}, message: {data}', slack=True, level='error')
        return wrapped_callback

class _SenderProc():
    def __init__(self,
               client_id: str,
               host: str,
               port: int,
               publish_queue_topics: list,
               allow_reconnect: bool,
               max_reconnect_attempts: int,
               reconnecting_time_wait: int):
        self.role = 'publisher'
        self.client = NATS()
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(
            self.client.connect(host + ':' + port, loop=self.loop, name=client_id + '__' + self.role))
        log('connected ' + self.role)
        self.connected = True
        self.run_publish_handlers(publish_queue_topics)

    def run_publish_handlers(self, publish_queue_topics):
        while self.connected is False:
            time.sleep(1)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run_publish_handlers(publish_queue_topics))

    async def _run_publish_handlers(self, redis_topics):
        try:
            if not redis_topics:
                return
            blocking_tasks = [self._handle_topic_queue_forever(rt) for rt in redis_topics]
            await asyncio.wait(blocking_tasks)
        except Exception as e:
            isr_log(f"ERROR _run_publish_handlers {os.environ['SERVICE_NAME']}: {str(e)}")

    async def _handle_topic_queue_forever(self, redis_topic_name):
        try:
            loop = asyncio.get_event_loop()
            publish_message_queue = RedisResponse(redis_topic_name, self.role)
            while True:
                if publish_message_queue.empty() is True:
                    await asyncio.sleep(0.001)
                    continue
                message = publish_message_queue.get()
                message = message.decode()
                loop.create_task(self._send(redis_topic_name, message))
        except Exception as e:
            log(f"_handle_topic_queue_forever error {os.environ['CLIENT_ID']}: " + str(e), level='error')

    async def _send(self, redis_topic, message):
        try:
            if self.validate_msg(message):
                if type(message) == str:
                    message = json.loads(message)
                topic = message.pop('topic')
                print(f'msg to topic: {topic}')
                if 'reply' in message:
                    try:
                        reply = message.pop('reply')
                        r = RedisResponse(reply)
                        if reply == False:
                            try:
                                await self.client.publish(topic, message.encode())
                                return
                            except Exception as e:
                                isr_log(f'sending NATS error: {str(e)}', level='error', phase='request',
                                        topic=topic, redis_topic=redis_topic)
                        timeout = message.pop('timeout', 10)
                        isr_id = reply
                        message = self.register_msg(message, topic, isr_id)
                        # isr_log(f'2REQUEST: isr_id: {isr_id} message: {message} topic: {topic} timeout {timeout}', phase='request')#, topic=topic, redis_topic=redis_topic)
                        response = await self.client.timed_request(topic, message.encode(), timeout=timeout)
                        # isr_log(f"5RESPONSE: isr_id: {isr_id} topic: {topic} response:"+str(response.data[:300]), phase='response')#, topic=topic, redis_topic=redis_topic)
                        r.put(response.data)
                    except Exception as e:
                        if 'isr_log' in locals():
                            isr_log(f"4ERROR isr_id: {isr_id} {message}", level='error')
                        isr_log(f'Invalid message: {message}, error: {str(e)}', level='error', phase='request',
                                redis_topic=redis_topic,
                                slack=True)
                else:
                    # isr_log(f'2PUBLISH: message: {message} topic: {topic} ')
                    # self.loop.call_soon(self.client.publish(topic, json.dumps(message).encode()))
                    await self.client.publish(topic, json.dumps(message).encode())
            else:
                isr_log(f'Invalid message: {message}', level='error', phase='request', redis_topic=redis_topic)
        except Exception as e:
            log('Request error :' + str(e), slack=True)

    def validate_msg(self, message):
        if type(message) is dict:
            return True
        elif type(message) is str and is_json(message):
            return True
        return False

    def register_msg(self, message, topic, isr_id=None):
        if type(message) is str and is_json(message):
            message = json.loads(message)
        return json.dumps(self.add_isr_id_if_absent(message, topic, isr_id))

    def add_isr_id_if_absent(self, message, topic, isr_id=None):
        if not 'isr-id' in message:
            if isr_id is None:
                message['isr-id'] = str(uuid.uuid4())
            else:
                message['isr-id'] = isr_id
        return message


if __name__ == "__main__":
    os.environ['SERVICE_NAME'] = 'NATSMPCli'
    client_id = 'NATSMPCli' + str(random.randint(1, 100))
    os.environ['CLIENT_ID'] = client_id

    def trades(topic, message):
        try:
            sent = json.loads(message)['sent']
            delivery_time = datetime.datetime.now().timestamp() - sent
            print(delivery_time)
        except Exception as e:
            pass


    print('start')
    cli = _MultiProcNATSClient()
    cli.client_id = client_id
    cli.host = '127.0.0.1'
    cli.port = "4222"
    cli.listen_topics_callbacks = {'topic2.wqe': [trades]}
    cli.publish_topics = ['topic2.wqe']
    cli.allow_reconnect = True
    cli.max_reconnect_attempts = 10
    cli.reconnecting_time_wait = 10
    cli.queue = ''
    cli.redis_host = '127.0.0.1'
    cli.redis_port = '6379'
    cli.pending_bytes_limit = 65536 * 1024 * 10
    cli.connect()
    time.sleep(3)


    # while True:
    #     time.sleep(100)
        # import random
        # b = 1
        # for i in range(100000000,10000000000):
        #     b = b + (i * random.randint(100000000,10000000000))