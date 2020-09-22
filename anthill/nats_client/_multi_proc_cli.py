import sys, os
import json
import uuid
import time
import random
import asyncio
import datetime
import multiprocessing
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
from queue import Empty
from asyncio.base_events import BaseEventLoop

from nats.aio.client import Client as NATS

from logger.logger import Logger, InterServicesRequestLogger
from utils.helper import start_thread, start_process, is_json
from utils.redis_queue import RedisQueue
from ._redis_response import RedisResponse

log = Logger(name='_MessengerClient_V3').log
# isr_log = InterServicesRequestLogger(name='InterServicesRequest_V3', separated_file=True).isr_log
isr_log = Logger(name='InterServicesRequest_V3', log_file=f'InterServicesRequest_V3_{os.environ["CLIENT_ID"]}.log').log


def transform_topic(topic):
    return ".".join([os.environ['CLIENT_ID'], topic.split('.')[-1]])


class _MultiProcClient:
    """
    Subinterface for NATSClient, create additional processes for sending and listening
    """
    def _connect(self):
        #TODO: check that all cls attr exists
        self.listen_message_queue = {}
        [self.listen_message_queue.update({topic: multiprocessing.Queue()}) for topic in self.listen_topics_callbacks]
        self.publish_message_queue = {}
        [self.publish_message_queue.update({transform_topic(topic): RedisResponse(transform_topic(topic))}) for topic in
         self.publish_topics]
        self.new_topics_redis_queue = multiprocessing.Queue()
        self.forced_closure = False
        self._launch()

    def _launch(self):
        self.client = _PublishClientInterface(self.publish_message_queue, self.new_topics_redis_queue, self)
        self._launch_listener()
        self._launch_sender()
        for topic, q in self.listen_message_queue.items():
            print(f'{os.environ["CLIENT_ID"]}*listening for topic: {topic}')
            start_thread(self._listen_incoming_messages_forever, args=(q, topic))

