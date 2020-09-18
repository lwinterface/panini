import sys, os
import time
import json
import random
import asyncio
import nats
import datetime
import uuid
from concurrent.futures import ProcessPoolExecutor

from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers

from logger.logger import Logger, InterServicesRequestLogger
from utils.helper import start_thread, is_json
from utils.singleton import singleton
import config.msgr_config as config

log = Logger(name='_MessengerClient_V2').log
isr_log = InterServicesRequestLogger(name='InterServicesRequest').isr_log

def sender_thread(*args):
    Sender().launch(*args)


def listener_thread(*args):
    Listener().launch(*args)


class _MessengerClient:
    """
    Subinterface for MessengerClient, create separate NATS client objects for sending and listening
    """

    def establish_connection(self,
                          client_id: str,
                          broker_host: str,
                          port: int,
                          listen_topics_callbacks: dict,
                          publish_topics: list,
                          allow_reconnect: bool or None,
                          max_reconnect_attempts: int or None,
                          reconnecting_time_wait: int or None,
                          queue="",
                          if_error='warning', #warning or error
                          # TODO: auth_credentialns
                          ):
        """
        :param client_id: instance identificator for NATS, str
        :param broker_host: '127.0.0.1' for local broker
        :param port: default '4333'
        :param listen_topics: dictfor example public.binance.order_book.*
        :param publish_topics: for example public.binance.order_book.BTC_USD
        :param allow_reconnect: False if you want to stop instance when connection lost
        :param max_reconnect_attempts:
        :param reconnecting_time_wait:
        :param if_error: type of logs for errors
        :return: {'success': True} if success otherwise  {'success': False, 'error': 'error description'}
        """
        if not hasattr(self, 'connected') or not self.connected:
            try:
                self.connected = False
                self.client_id = client_id
                self.broker_host = broker_host
                self.port = port
                self.listen_topics_callbacks = listen_topics_callbacks
                self.publish_topics = publish_topics
                self.allow_reconnect = allow_reconnect
                self.max_reconnect_attempts = max_reconnect_attempts
                self.reconnecting_time_wait = reconnecting_time_wait
                self.queue = queue
                self.if_error = if_error
                self.loop = asyncio.get_event_loop()
                start_thread(self._launch_listener, args=(self.loop,))
                time.sleep(2)
                self._launch_sender(self.loop)
                return self.client
            except Exception as e:
                log(str(e), level='error', print_=True, slack=True)
                raise Exception({'success': False, 'error': str(e)})
        else:
            log(str('Client has been already connected'),print_=True, slack=True)
            return self.client

    def _launch_listener(self, loop):
        start_thread(listener_thread, args=(loop,
                  self.client_id,
                  self.broker_host,
                  self.port,
                  self.listen_topics_callbacks,
                  self.publish_topics,
                  self.allow_reconnect,
                  self.max_reconnect_attempts,
                  self.reconnecting_time_wait,
                  self.if_error))

    def _launch_sender(self, loop):
        sender_client = Sender()
        sender_client.launch(loop,
                    self.client_id,
                    self.broker_host,
                    self.port,
                    self.listen_topics_callbacks,
                    self.publish_topics,
                    self.allow_reconnect,
                    self.max_reconnect_attempts,
                    self.reconnecting_time_wait,
                    self.if_error)
        self.client = sender_client

    def add_listen_topic_callback(self, topic, callback):
        if not topic in self.listen_topics_callbacks:
            self.listen_topics_callbacks[topic] = []
        self.listen_topics_callbacks[topic].append(callback)
        self.loop.run_until_complete(self.client.subscribe(topic, cb=self.message_handler))

class MessengerBase:
    def create_connection(self,
                          loop: asyncio.AbstractEventLoop,
                          client_id: str,
                          broker_host: str,
                          port: int,
                          listen_topics_callbacks: list,
                          publish_topics: list or None,
                          allow_reconnect=True,
                          max_reconnect_attempts=10,
                          reconnecting_time_wait=10,
                          if_error='warning', #warning or error
                          is_listener=False,
                          # TODO: auth_credentialns
                          ):
        if not hasattr(self, 'connected') or not self.connected:
            self.connected = False
            self.client_id = client_id
            self.broker_host = broker_host
            self.port = port
            self.listen_topics_callbacks = listen_topics_callbacks
            self.publish_topics = publish_topics
            self.allow_reconnect = allow_reconnect
            self.max_reconnect_attempts = max_reconnect_attempts
            self.reconnecting_time_wait = reconnecting_time_wait
            self.if_error = if_error
            self.loop = loop
            self.is_listener = is_listener
            script_position = os.path.dirname(sys.argv[0])

    def _launch(self, loop):
        self.loop = loop
        self.loop.run_until_complete(self._connect())

    async def _connect(self):
        #TODO: authorization
        self.client = NATS()
        self.server = self.broker_host+':'+self.port
        kwargs = {'servers': self.server, 'loop': self.loop, 'name': self.client_id}
        if self.allow_reconnect:
            kwargs['allow_reconnect'] = self.allow_reconnect
        if self.max_reconnect_attempts:
            kwargs['max_reconnect_attempts'] = self.max_reconnect_attempts
        if self.reconnecting_time_wait:
            kwargs['reconnect_time_wait'] = self.reconnecting_time_wait
        await self.client.connect(**kwargs)
        self.connected = True

        if self.is_listener:
            log('connected listener', print_=True)
            listen_topics_callbacks = self.listen_topics_callbacks
            for topic, callbacks in listen_topics_callbacks.items():
                for callback in callbacks:
                    wrapped_callback = self.wrap_callback(callback, self.client)
                    await self.client.subscribe(topic, cb=wrapped_callback, pending_bytes_limit=65536 * 1024 * 10)

            await self._listening()
        else:
            log('connected publisher', print_=True)

    def wrap_callback(self, cb, cli):
        async def wrapped_callback(msg):
            subject = msg.subject
            data = msg.data.decode()
            if not msg.reply == '':
                try:
                    data = json.loads(data)
                    isr_log(data, topic=subject)
                    isr_id = data.pop('isr-id')
                    reply = cb(subject, data)
                    reply['isr-id'] = isr_id
                    isr_log(reply, topic=subject)
                    reply = json.dumps(reply)
                    await cli.publish(msg.reply, reply.encode())
                except Exception as e:
                    if not 'isr_id' in locals():
                        isr_id = 'Unknown'
                    isr_log(str(e), level='error', topic=subject, isr_id=isr_id)
            else:
                cb(subject, data)
        return wrapped_callback

    def disconnect(self):
        self.loop.run_until_complete(self.aio_disconnect())
        log('Disconnected', level='warning')

    async def aio_disconnect(self):
        await self.client.drain()
        log('Disconnected', level='warning')

    def check_connection(self):
        if self.client._status is NATS.CONNECTED:
            log('NATS Client status: CONNECTED')
            return True
        log('NATS Client status: DISCONNECTED', level='warning')


class Listener(MessengerBase):
    def launch(self,
               loop: asyncio.AbstractEventLoop,
               client_id: str,
               broker_host: str,
               port: int,
               listen_topics_callbacks: list,
               publish_topics: list or None,
               allow_reconnect: bool,
               max_reconnect_attempts: int,
               reconnecting_time_wait: int,
               if_error='warning',  # warning or error
               is_listener=True, ):
        self.create_connection(
            loop=loop,
            client_id=client_id,
            broker_host=broker_host,
            port=port,
            listen_topics_callbacks=listen_topics_callbacks,
            publish_topics=publish_topics,
            allow_reconnect=allow_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnecting_time_wait=reconnecting_time_wait,
            if_error=if_error,
            is_listener=is_listener)
        start_thread(self._launch, args=(self.loop,))

    async def _listening(self):
        while True:
            await asyncio.sleep(1)

    async def message_handler(self, msg):
        subject = msg.subject
        data = msg.data.decode()
        # await self._handle_message(subject, data)
        reply = self._handle_message(subject, data)
        if reply:
            await self.client.publish(msg.reply, reply)

    def _handle_message(self, subject, data):
        callbacks = self.listen_topics_callbacks[subject]
        reply = []
        for callback in callbacks:
            reply.append(callback(subject, data))
        return reply

    async def error_cb(self, e):
        if type(e) is nats.aio.errors.ErrSlowConsumer:
            msg = ("Slow consumer error, unsubscribing from handling further messages...")
            log(msg, type='error', print_=True, slack=True)

    def add_listen_topic_callback(self, topic, callback):
        if not topic in self.listen_topics_callbacks:
            self.listen_topics_callbacks[topic] = []
        self.listen_topics_callbacks[topic].append(callback)
        self.loop.run_until_complete(self.client.subscribe(topic, cb=self.message_handler))

class Sender(MessengerBase):
    def launch(self,
               loop: asyncio.AbstractEventLoop,
               client_id: str,
               broker_host: str,
               port: int,
               listen_topics_callbacks: list,
               publish_topics: list or None,
               allow_reconnect: bool,
               max_reconnect_attempts: int,
               reconnecting_time_wait: int,
               if_error='warning',  # warning or error
               is_listener=False, ):
        self.create_connection(
            loop=loop,
            client_id=client_id,
            broker_host=broker_host,
            port=port,
            listen_topics_callbacks=listen_topics_callbacks,
            publish_topics=publish_topics,
            allow_reconnect=allow_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnecting_time_wait=reconnecting_time_wait,
            if_error=if_error,
            is_listener=is_listener)
        self._launch(self.loop)
        # start_thread(self._launch, args=(self.loop,))

    def publish(self, message, topic, reply_to=None):
        asyncio.run(self.aio_publish(message, topic))

    def publish_request(self, message, topic, timeout=10, unpack=None): #TODO: implement unpack logic
        return asyncio.run(self.aio_publish_request(message, topic, timeout))

    def publish_request_reply_to_another_topic(self, message, topic, reply_to=None):
        raise NotImplementedError

    async def aio_publish(self, message, topic, force=None):
        message = message.encode()
        await self.client.publish(topic, message)

    async def aio_publish_request(self, message, topic, timeout=10, unpack=True):
        # isr_log(f'1REQUEST message: {message}', phase='request', topic=topic)
        if self.validate_msg(message):
            message = self.register_msg(message, topic)
            message = message.encode()
            response = await self.client.timed_request(topic, message, timeout=timeout)
            isr_log(response.data, phase='response', topic=topic)
            return response
        isr_log(f'Invalid message: {message}', level='error', phase='request', topic=topic)

    async def aio_publish_request_reply_to_another_topic(self, message, topic, reply_to=None):
        raise NotImplementedError

    def validate_msg(self, message):
        if type(message) is dict:
            return True
        elif type(message) is str and is_json(message):
            return True
        return False

    def register_msg(self, message, topic):
        if type(message) is str and is_json(message):
            message = json.loads(message)
        return json.dumps(self.add_isr_id_if_absent(message, topic))

    def add_isr_id_if_absent(self, message, topic):
        if not 'isr-id' in message:
            message['isr-id'] = str(uuid.uuid4())
        isr_log(message, phase='request', topic=topic)
        return message





#for test
if __name__ == "__main__":

    def msg_generator():
        is_msgs_required = True
        time.sleep(5)
        while True:
            if is_msgs_required:
                n = 0
                for i in range(100):
                    msg = f' =======>>>>>>some message number {str(n)}'
                    cli.client.publish(msg, 'topic2.wqe')
                    n += 1
                time.sleep(1)


    def reciever_msg_handler(topic, msg):
        print(f"reciever_msg_handler ==> topic: {topic}, msg: {msg}")


    cli = _MessengerClient()
    cli.establish_connection(
        client_id='client'+str(random.randint(1,100)),
        broker_host=config.BROKER_HOST,
        port=config.PORT,
        listen_topics_callbacks={'topic2.wqe':reciever_msg_handler},
        publish_topics=['topic2.wqe',],
        allow_reconnect=config.ALLOW_RECONNECT,
        max_reconnect_attempts=config.MAX_RECONNECT_ATTEMPTS,
        reconnecting_time_wait=config.RECONNECTING_TIME_WAIT,
    )
    time.sleep(3)
    start_thread(msg_generator)
    import random

    while True:
        b = 1
        for i in range(100000000,10000000000):
            b = b + (i * random.randint(100000000,10000000000))