import asyncio
import time
from typing import Union
from panini.exceptions import InitializingTaskError


class TaskManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """

    def __init__(self):
        self._tasks = []
        self._on_start_tasks = []
        self._loop = asyncio.get_event_loop()

    @property
    def tasks(self):
        return self._tasks

    @property
    def on_start_tasks(self):
        return self._on_start_tasks

    def register_on_start_task(self):
        def wrapper(task):
            self._check_task(task)
            self._on_start_tasks.append(task)
        return wrapper

    def register_task(self, interval: Union[float, int] = None):
        def wrapper(task):
            self._check_task(task)
            if interval:
                task = self.wrapper_for_interval_task(interval, task)
            self._tasks.append(task)

        return wrapper

    def register_single_task(self):
        def wrapper(task):
            self._check_task(task)
            self._tasks.append(task)
        return wrapper

    def register_interval_task(self, interval: int or float):
        def wrapper(task):
            self._check_task(task)
            interval_task = self.wrapper_for_interval_task(interval, task)
            self._tasks.append(interval_task)
            # self._loop.create_task(interval_task())
        return wrapper

    def wrapper_for_interval_task(self, interval, task):
        async def wrapper(**kwargs):
            while True:
                try:
                    start = time.time()
                    await task(**kwargs)
                    duration = time.time() - start

                    if duration < interval:
                        await asyncio.sleep(interval - duration)

                except InitializingTaskError:
                    # TODO: warning log
                    pass

        return wrapper

    def _check_task(self, task):
        if not asyncio.iscoroutinefunction(task):
            raise InitializingTaskError("Only coroutine tasks allowed")

    def create_tasks(self):
        loop = asyncio.get_event_loop()
        for task in self._tasks:
            loop.create_task(task())


