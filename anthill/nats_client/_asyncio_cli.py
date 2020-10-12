import sys, os
import time
import json
import random
import asyncio
import datetime
import uuid
from nats.aio.client import Client as NATS
from ..logger.logger import Logger, InterServicesRequestLogger
from ..utils.helper import is_json, run_coro_threadsafe
from ..exceptions import EventHandlingError

log = Logger(name='_AsyncioNATSClient').log
isr_log = InterServicesRequestLogger(name='InterServicesRequest_AsyncioNATSClient').isr_log

class _AsyncioNATSClient(object):
    """
    Subinterface for NATSClient, create asyncio NATS connection for sending and listening
    """

    def __init__(self, base_obj):
        self.__dict__ = base_obj.__dict__
        #TODO: check that all cls attr exists
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self._establish_connection())

    async def _establish_connection(self):
        # TODO: authorization
        self.client = NATS()
        self.server = self.host + ':' + str(self.port)
        kwargs = {'servers': self.server, 'loop': self.loop, 'name': self.client_id}
        if self.allow_reconnect:
            kwargs['allow_reconnect'] = self.allow_reconnect
        if self.max_reconnect_attempts:
            kwargs['max_reconnect_attempts'] = self.max_reconnect_attempts
        if self.reconnecting_time_wait:
            kwargs['reconnect_time_wait'] = self.reconnecting_time_wait
        kwargs.update(self.auth)
        await self.client.connect(**kwargs)
        if self.client.is_connected:
            listen_topics_callbacks = self.listen_topics_callbacks
            for topic, callbacks in listen_topics_callbacks.items():
                for callback in callbacks:
                    await self.aio_subscribe_new_topic(topic, callback)
    
    def subscribe_new_topic(self, topic, callback):
        self.loop.run_until_complete(self.aio_subscribe_new_topic(topic, callback))
        
    async def aio_subscribe_new_topic(self, topic, callback):
        wrapped_callback = self.wrap_callback(callback, self)
        await self.client.subscribe(topic, queue=self.queue, cb=wrapped_callback,
                                    pending_bytes_limit=self.pending_bytes_limit)

    def wrap_callback(self, cb, cli):
        async def wrapped_callback(msg):

            async def callback(cb, subject, data, reply_to=None, isr_id=None):
                if asyncio.iscoroutinefunction(cb):
                    async def coro_callback_with_reply(subject, data, reply_to, isr_id):
                        try:
                            reply = await cb(subject, data)
                            if reply_to:
                                if reply is None:
                                    return
                                reply['isr-id'] = isr_id
                                reply = json.dumps(reply)
                                await cli.aio_publish(reply, reply_to)
                        except EventHandlingError as e:
                            if not 'reply' in locals():
                                reply = ""
                            raise EventHandlingError(
                                f"callback_when_future_finished ERROR: {str(e)}, reply if exist: {reply}")
                    try:
                        asyncio.ensure_future(coro_callback_with_reply(subject, data, reply_to, isr_id))
                        # await coro_callback_with_reply(subject, data, reply_to, isr_id)
                    except EventHandlingError as e:
                        raise Exception(f"callback ERROR: {str(e)}")
                else:
                    return cb(subject, data)

            async def handle_message_with_response(cli, data, reply_to, isr_id):
                # isr_log(f"3RECIEVED REQUEST msg: isr_id: {isr_id} reply_to:{reply_to} {data}, {subject}")
                reply = await callback(cb, subject, data, reply_to, isr_id)
                if reply:
                    reply['isr-id'] = isr_id
                    reply = json.dumps(reply)
                    # isr_log(f"4SENDING-RESPONSE msg: isr_id: {isr_id} reply_to:{reply_to}({type(reply_to)}) {data}, {subject}")
                    await cli.aio_publish(reply, reply_to)

            subject = msg.subject
            raw_data = msg.data.decode()
            data = json.loads(raw_data)
            if not msg.reply == '':
                reply_to = msg.reply
            elif 'reply_to' in data:
                reply_to = data.pop('reply_to')
            else:
                # isr_log(f"3RECIEVED PUBL msg: {data[:150] if len(data) < 150 else data}, {subject}")
                await callback(cb, subject, data)
                return
            isr_id = data.get('isr-id', str(uuid.uuid4())[:10])
            try:
                await handle_message_with_response(cli, data, reply_to, isr_id)
            except EventHandlingError as e:
                if not 'isr_id' in locals():
                    isr_id = 'Absent or Unknown'
                isr_log("4SENDING RESPONSE error msg: " + str(e), level='error', topic=subject, isr_id=isr_id)

        return wrapped_callback

    def publish(self, message, topic):
        asyncio.ensure_future(self.aio_publish(message, topic))

    def publish_request_with_reply_to_another_topic(self, message, topic, reply_to=None):
        asyncio.ensure_future(self.aio_publish_request_with_reply_to_another_topic(message, topic, reply_to))

    def publish_from_another_thread(self, message, topic):
        self.loop.call_soon_threadsafe(self.publish, message, topic)

    def publish_request(self, message, topic, timeout=10, unpack=None):
        asyncio.ensure_future(self.aio_publish_request(message, topic, timeout, unpack))

    def publish_request_from_another_thread(self, message, topic, loop, timeout=10, unpack=None):
        coro = self.aio_publish_request(message, topic, timeout, unpack)
        return loop.run_until_complete(run_coro_threadsafe(coro, self.loop))

    async def aio_publish(self, message, topic, force=False, nonjson=False):
        if type(message) is dict and nonjson is False:
            message = json.dumps(message)
            message = message.encode()
        elif type(message) is str:
            message = message.encode()
        elif type(message) is bytes:
            pass
        if not force:
            await self.client.publish(topic, message)
        else:
            raise NotImplementedError

    async def aio_publish_soon(self, message, topic):
        if is_json(message) is False:
            message = json.dumps(message)
        message = message.encode()
        await self.client.publish(topic, message)

    async def aio_publish_force(self, message, topic):
        raise NotImplementedError

    async def aio_publish_request(self, message, topic, timeout=10, unpack=None):
        if type(message) == str:
            message = json.loads(message)
        if self.validate_msg(message):
            if not 'isr-id' in message:
                isr_id = str(uuid.uuid4())
                message = self.register_msg(message, isr_id)
            else:
                message = json.dumps(message)
            message = message.encode()
            response = await self.client.request(topic, message, timeout=timeout)
            response = response.data
            # isr_log(f'6RESPONSE message: {message}', phase='response', topic=topic)
            if unpack:
                response = json.loads(response)
            return response
        isr_log(f'Invalid message: {message}', level='error', topic=topic)

    async def aio_publish_request_with_reply_to_another_topic(self, message, topic, reply_to=None):
        message['isr-id'] = str(uuid.uuid4())[:10]
        if is_json(message):
            message = json.loads(message)
            message['reply_to'] = reply_to
        else:
            message['reply_to'] = reply_to
        message = json.dumps(message)
        # isr_log(f'1REQUEST_to_another_topic message: {message}', phase='request', topic=topic)
        await self.aio_publish(message, topic)

    def validate_msg(self, message):
        if type(message) is dict:
            return True
        elif type(message) is str and is_json(message):
            return True
        return False

    def register_msg(self, message, isr_id=None):
        if type(message) is str and is_json(message):
            message = json.loads(message)
        return json.dumps(self.add_isr_id_if_absent(message, isr_id))

    def add_isr_id_if_absent(self, message, isr_id=None):
        if not 'isr-id' in message:
            if isr_id is None:
                message['isr-id'] = str(uuid.uuid4())
            else:
                message['isr-id'] = isr_id
        return message

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








# for test
if __name__ == "__main__":
    os.environ['SERVICE_NAME'] = 'NATSAIOCli'

    def msg_generator():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        is_msgs_required = True
        time.sleep(5)
        print('msg_generator started')
        while True:
            if is_msgs_required:
                n = 0
                start = datetime.datetime.now().timestamp()
                for i in range(1000):
                    msg = f' =======>>>>>>some message number {str(n)}'
                    cli.publish_from_another_thread(msg, 'topic2.wqe', loop)
                    print(f"SENT ==> topic: 'topic2.wqe', msg: {msg}")
                    n += 1
                print(f'duration: {datetime.datetime.now().timestamp() - start}')
                time.sleep(1)
                return

    def msg_req_generator():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        is_msgs_required = True
        time.sleep(5)
        print('msg_generator started')
        while True:
            if is_msgs_required:
                n = 0
                start = datetime.datetime.now().timestamp()
                for i in range(1000):
                    msg = {'data': f' =======>>>>>>some message number {str(i)}'}
                    result = cli.publish_request_from_another_thread(msg, 'topic2.wqe', loop)
                    print(f"SENT ==> topic: 'topic2.wqe', result: {result}")
                    n += 1
                print(f'duration: {datetime.datetime.now().timestamp() - start}')
                time.sleep(1)
                return

    async def amsg_generator(cli):
        is_msgs_required = True
        time.sleep(5)
        print('amsg_generator started')
        while True:
            if is_msgs_required:
                n = 0
                start = datetime.datetime.now().timestamp()
                for i in range(1000):
                    msg = f' =======>>>>>>some message number {str(n)}'
                    await cli.aio_publish(msg, 'topic2.wqe')
                    # cli.publish(msg, 'topic2.wqe')
                    print(f"SENT ==> topic: 'topic2.wqe', msg: {msg}")
                    n += 1
                print(f'duration: {datetime.datetime.now().timestamp() - start}')
                time.sleep(1)
                return

    async def amsg_req_generator(cli):
        is_msgs_required = True
        time.sleep(5)
        print('amsg_generator started')
        while True:
            if is_msgs_required:
                n = 0
                start = datetime.datetime.now().timestamp()
                for i in range(1000):
                    msg = {'data': f' =======>>>>>>some message number {str(n)}'}
                    response = await cli.aio_publish_request(msg, 'topic2.wqe')
                    # response = cli.publish_request(msg, 'topic2.wqe')
                    # cli.publish(msg, 'topic2.wqe')
                    print(f"SENT ==> topic: 'topic2.wqe', response: {response}")
                    n += 1
                print(f'duration: {datetime.datetime.now().timestamp() - start}')
                time.sleep(1)
                return

    async def amsg_req_generator_v2(cli):
        time.sleep(5)
        print('amsg_generator started')

        async def request(i):
            result = await cli.aio_publish_request({'data': f' =======>>>>>>some request number {str(i)}'},
                                                   'topic2.wqe', timeout=60)
            print(result)
            return result

        start = datetime.datetime.now().timestamp()
        tasks = [request(str(i)) for i in range(1000)]
        await asyncio.gather(*tasks)
        print(f'duration: {datetime.datetime.now().timestamp() - start}')
        time.sleep(1)
        return

    async def amsg_generator_v2(cli):
        is_msgs_required = True
        time.sleep(5)
        print('amsg_generator started')
        start = datetime.datetime.now().timestamp()
        tasks = [cli.aio_publish(f' =======>>>>>>some message number {str(i)}', 'topic2.wqe') for i in
                 range(1000)]
        await asyncio.gather(*tasks)
        duration = f'duration: {datetime.datetime.now().timestamp() - start}'
        # isr_log(duration)
        print(duration)

    async def subscribe_handler(msg):
        print("Got message: ", msg.subject, msg.reply, msg.data)

    async def reciever_msg_handler(topic, msg):
        response = {"success": True, "data": f"RECIEVED ==> topic: {topic}, msg: {msg}"}
        print(f"yau! {msg}")
        await asyncio.sleep(1)
        return response

    print('start')
    cli = _AsyncioNATSClient()
    cli.client_id = 'client' + str(random.randint(1, 100))
    cli.host = '127.0.0.1'
    cli.port = "4222"
    cli.listen_topics_callbacks = {'topic2.wqe': [reciever_msg_handler]}
    cli.allow_reconnect = True
    cli.max_reconnect_attempts = 10
    cli.reconnecting_time_wait = 10
    cli.queue = ''
    cli.pending_bytes_limit = 65536 * 1024 * 10
    cli.connect()
    time.sleep(3)
    # start_thread(msg_generator)
    # start_thread(msg_req_generator)
    loop = asyncio.get_event_loop()
    # loop.create_task(job(cli.client))
    # loop.create_task(amsg_generator_v2(cli))
    # loop.create_task(amsg_req_generator(cli))
    # loop.create_task(amsg_req_generator_v2(cli))
    tasks = asyncio.all_tasks(loop)
    loop.run_until_complete(asyncio.gather(*tasks))
    loop.run_forever()
    print('finish')
