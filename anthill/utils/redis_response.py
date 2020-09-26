import os
import time
import datetime

from nats.aio.errors import ErrTimeout, NatsError

from utils.redis_queue import RedisQueue
from logger.logger import Logger

log = Logger(name='_MessengerClient_V3').log
# HOST = '127.0.0.1'

class ResponseData:
    def __init__(self, data):
        self.data = data

class RedisResponse(RedisQueue):
    def __init__(self, name, namespace='response', host='127.0.0.1', port='6379', db=0, waiting_btwn_check=0.05):
        if 'SERVICE_NAME' in os.environ:
            if '_sender_client' in os.environ['SERVICE_NAME']:
                service_name = os.environ['SERVICE_NAME'].replace('_sender_client','')
            else:
                service_name = os.environ['SERVICE_NAME']
            self._name = '_'.join([service_name, name])
        else:
            self._name = '_'.join(['Unknown', name])
        super().__init__(name, namespace, host, port, db)
        self.waiting_btwn_check = waiting_btwn_check

    def return_response_when_appeared(self, topic=None, timeout=30):
        started = datetime.datetime.now().timestamp()
        while datetime.datetime.now().timestamp() - started < timeout:
            try:
                if self.empty():
                    time.sleep(0.05)
                    continue
                return ResponseData(self.get())
            except Exception as e:
                    log('RedisResponse error: ', str(e))
        msg = 'Nats client timeout'
        log(f"Waiting for response from redis ERROR: {msg}, topic: {topic}", level='error')
        raise ErrTimeout(msg)