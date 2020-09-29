import time
import asyncio
from typing import Callable
from .exceptions import SerializationError, InitializingIntevalTaskError



class EventManager:
    """
    Collect all functions from each module wrapped by @app.subscription or @EventManager.subscribe
    """
    SUBSCRIPTIONS = {}

    @staticmethod
    def subscribe(subsciption: list or str, serializator: type = None):
        def wrapper(function):
            function = EventManager.wrap_function_by_serializer(function, serializator)
            if type(subsciption) is list:
                for s in subsciption:
                    EventManager._check_subscription(s)
                    EventManager.SUBSCRIPTIONS[s].append(function)
            else:
                EventManager._check_subscription(subsciption)
                EventManager.SUBSCRIPTIONS[subsciption].append(function)
            return function
        return wrapper

    @staticmethod
    def wrap_function_by_serializer(function, serializator):
        def wrapper(topic, message):
            try:
                if serializator is not None:
                    message = serializator.validated_message(message)
            except SerializationError as e:
                error = f'topic: {topic} error: {str(e)}'
                raise SerializationError(error)
            return function(topic, message)
        return wrapper

    @staticmethod
    def _check_subscription(subsciption):
        if not subsciption in EventManager.SUBSCRIPTIONS:
            EventManager.SUBSCRIPTIONS[subsciption] = []



class TaskManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """
    TASKS = []

    @staticmethod
    def task(**kwargs):
        def wrapper(task):
            TaskManager._check_task(task)
            TaskManager.TASKS.append(task)
            return task
        return wrapper

    @staticmethod
    def _check_task(task):
        #TODO
        pass



class IntervalTaskManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """
    INTERVAL_TASKS = {}

    @staticmethod
    def timer_task(interval: float or int):
        def wrapper(interval_task: Callable):
            IntervalTaskManager._check_timer_task(interval, interval_task)
            if asyncio.iscoroutinefunction(interval_task):
                interval_task = IntervalTaskManager.wrap_coro_by_interval(interval, interval_task)
            else:
                interval_task = IntervalTaskManager.wrap_function_by_interval(interval, interval_task)
            if not interval in IntervalTaskManager.INTERVAL_TASKS:
                IntervalTaskManager.INTERVAL_TASKS[interval] = []
            IntervalTaskManager.INTERVAL_TASKS[interval].append(interval_task)
            return interval_task
        return wrapper

    @staticmethod
    def wrap_coro_by_interval(interval, interval_task):
        async def wrapper(**kwargs):
            while True:
                try:
                    await interval_task(**kwargs)
                    await asyncio.sleep(interval)
                except InitializingIntevalTaskError as e:
                    #TODO: warning log
                    pass
        return wrapper

    @staticmethod
    def wrap_function_by_interval(interval, interval_task):
        def wrapper(**kwargs):
            while True:
                try:
                    interval_task(**kwargs)
                    time.sleep(interval)
                except InitializingIntevalTaskError as e:
                    #TODO: warning log
                    pass
        return wrapper

    @staticmethod
    def _check_timer_task(interval, interval_task):
        #TODO
        pass