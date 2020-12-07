import time
import threading
import contextlib
import uvicorn
from aiohttp import web
from fastapi import FastAPI

class HTTPServer:
    def __init__(self, base_app, host: str = None, port: int = None, web_app = None, web_framework='fastapi'):
        self.app = base_app
        self.host = host
        self.port = port
        self.web_framework = web_framework
        if web_app:
            self.web_app = web_app
        else:
            if self.web_framework == 'fastapi':
                self.web_app = FastAPI()
            elif self.web_framework == 'aiohttp':
                self.web_app = web.Application()

    def start_server(self, uvicorn_app_target: str = None):
        self._start_server(uvicorn_app_target)

    def _start_server(self, uvicorn_app_target: str = None):
        if self.web_framework == 'fastapi':
            config = uvicorn.Config(uvicorn_app_target, host=self.host, port=self.port, log_level="info")
            self.server = Server(config=config)
        elif self.web_framework == 'aiohttp':
            self.web_app.add_routes(self.app.http)
            web.run_app(self.web_app, host=self.host, port=self.port)

class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()

