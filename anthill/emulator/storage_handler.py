import json
import os
import time
from datetime import datetime


class StorageHandler:

    def __init__(self, client_id: str, client_name: str, queue: str, nats_host: str = "127.0.0.1", nats_port: int = 4222):

        from ..app import App
        print("sub:", f'storage.{client_name}.>')
        self.app = App(
            service_name=f'storage_{client_id}',
            host=nats_host,
            port=nats_port,
            app_strategy='asyncio',
            allocation_quenue_group=queue,
            subscribe_topics_and_callbacks={f'storage.{client_name}.>': [self._write]}
        )
        self.log = self.app.logger.log
        # self.app.subscribe_topic(f'storage.{client_name}.{client_id}.>', self._write)

        root_dir = "./storage"
        self.session_dir = os.path.join(root_dir, datetime.now().strftime("%y-%d-%m_%H-%M"))
        if not os.path.isdir(self.session_dir):
            os.makedirs(self.session_dir)
        self.storage_file = os.path.join(self.session_dir, f"{client_name}.trace")

    def _write(self, topic, message):
        storage, service_name, message_type, *args = topic.split(".")
        topic = ".".join(args)
        event = {
            "timestamp": time.time(),
            "service_name": service_name,
            # "service_id": service_id,
            "message_type": message_type,
            "topic": topic,
            "message": message
        }
        self.log(f'storage got a message: {topic}|{message}')

        with open(self.storage_file, 'a') as file:
            file.write(json.dumps(event) + '\n')

    def run(self):
        self.app.start()
