import asyncio
import aiohttp
from packaging import version
from aiohttp import web
from aiohttp.web_routedef import RouteTableDef


class HTTPServer:
    def __init__(
        self,
        routes: RouteTableDef,
        loop: asyncio.AbstractEventLoop,
        host: str = None,
        port: int = None,
        web_app: web.Application = None,
        web_server_params=None,
        middlewares: list = None,
    ):
        if web_server_params is None:
            web_server_params = {}

        self.routes = routes
        self.host = host
        self.port = port
        self.web_server_params = web_server_params
        self.loop = loop

        if web_app:
            self.web_app = web_app
        else:
            self.web_app = web.Application(middlewares=middlewares)

    def start_server(self):
        self._start_server()

    def _start_server(self):
        self.web_app.add_routes(self.routes)
        if version.parse(aiohttp.__version__) >= version.parse("3.8.0"):
            self.web_server_params["loop"] = self.loop
        web.run_app(
            self.web_app, host=self.host, port=self.port, **self.web_server_params
        )
