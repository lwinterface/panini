from ..utils.helper import start_process

def run_absorber(client_id, num_executors, nats_host, nats_port, arctic_host, arctic_port):
    queue_name = f'absorber_for_{client_id}_group'
    for _ in range(num_executors):
        start_process(_run_absorber, args=(client_id, queue_name, nats_host, nats_port, arctic_host, arctic_port))

def _run_absorber(client_id, queue_name, nats_host, nats_port, arctic_host, arctic_port):
    AbsorberExecutor(client_id=client_id,
                     queue=queue_name,
                     nats_host=nats_host,
                     nats_port=nats_port,
                     arctic_host=arctic_host,
                     arctic_port=arctic_port).run_absorber()

class AbsorberExecutor:
    def __init__(self,
                 client_id: str,
                 queue: str,
                 nats_host: str = "127.0.0.1",
                 nats_port: int = 4222,
                 arctic_host: str = "127.0.0.1",
                 arctic_port: int = 27017):
        self.create_app(client_id, queue, nats_host, nats_port)
        self.connect_to_db(client_id, arctic_host, arctic_port)

    def create_app(self, client_id, queue, nats_host, nats_port):
        #create app with one listener for topic 'absorber.<client_id>.<clients topic>' that listen fot all incoming messages
        from ..app import App
        absorber_topic = f'absorber.{client_id}.>'
        self.app = App(
            service_name=f'absorber_for_{client_id}',
            host=nats_host,
            port=nats_port,
            app_strategy='asyncio',
            allocation_quenue_group=queue,
            subscribe_topics_and_callbacks={absorber_topic: [self.write_to_db]}
        )
        self.log = self.app.logger.log

    def connect_to_db(self, client_id, arctic_host, arctic_port):
        #TODO
        pass

    def write_to_db(self, topic, message):
        self.log(f'absorber got message: {topic}|{message}')

    def run_absorber(self):
        self.app.start()