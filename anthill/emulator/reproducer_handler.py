import os
import time
from datetime import datetime

from anthill.app import App


class StorageHandler:

    def __init__(self, client_id: str, client_name: str, queue: str, nats_host: str = "127.0.0.1", nats_port: int = 4222):
        self.app = App(
            service_name=f'storage_{client_id}',
            host=nats_host,
            port=nats_port,
            app_strategy='asyncio',
            allocation_quenue_group=queue
        )
        self.log = self.app.logger.log
        self.app.subscribe_topic(f'storage.{client_name}.{client_id}.>', self._write)

        root_dir = "./storage"
        self.session_dir = os.path.join(root_dir, datetime.now().strftime("%y-%d-%m_%H-%M"))
        self.storage_file = os.path.join(self.session_dir, f"{client_name}.{client_id}")

    def _write(self, topic, message):
        storage, service_name, service_id, message_type, *args = topic.split(".")
        topic = ".".join(args)
        event = {
            "timestamp": time.time(),
            "service_name": service_name,
            "service_id": service_id,
            "message_type": message_type,
            "topic": topic,
            "message": message
        }
        self.log(f'storage got a message: {topic}|{message}')

        with open(self.storage_file, 'a') as file:
            file.write(event)

    def run(self):
        self.app.start()
