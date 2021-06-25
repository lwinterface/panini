import os

from aiohttp import web


class HTTPServer:
    def __init__(
        self,
        base_app,
        host: str = None,
        port: int = None,
        web_app: web.Application = None,
    ):
        self.app = base_app
        self.routes = base_app.http
        self.host = host
        self.port = port
        if web_app:
            self.web_app = web_app
        else:
            self.web_app = web.Application()

    def start_server(self):
        self._start_server()

    def _start_server(self):
        self.web_app.add_routes(self.routes)
        if os.environ.get("PANINI_TEST_MODE"):
            # do not handle signals while testing
            web.run_app(
                self.web_app, host=self.host, port=self.port, handle_signals=False
            )

        else:
            web.run_app(self.web_app, host=self.host, port=self.port)
