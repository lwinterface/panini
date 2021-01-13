import time
import asyncio

from . import exceptions
from typing import Callable
from .exceptions import SerializationError, InitializingIntevalTaskError, NotReadyError, BaseError


class _EventManager:
    """
    Collect all functions from each module wrapped by @app.subscription or @EventManager.subscribe
    """
    SUBSCRIPTIONS = {}

    def listen(self, topic: list or str, serializator: type = None,
               dynamic_subscription: bool = False, non_store: bool = False):
        def wrapper(function):
            function = _EventManager.wrap_function_by_serializer(function, serializator)
            if type(topic) is list:
                for t in topic:
                    _EventManager._check_subscription(t)
                    _EventManager.SUBSCRIPTIONS[t].append(function)
            else:
                _EventManager._check_subscription(topic)
                _EventManager.SUBSCRIPTIONS[topic].append(function)
            return function
        if dynamic_subscription:
            if type(topic) is list:
                for t in topic:
                    self._subscribe(t, wrapper)
            else:
                self._subscribe(topic, wrapper)
        return wrapper

    def _subscribe(self, topic, function):
        if not hasattr(self, 'connector') or self.connector.check_connection is False:
            raise NotReadyError('Something wrong. NATS client should be connected first')
        self.subscribe_topic(topic, function)


    @staticmethod
    def wrap_function_by_serializer(function, serializator):
        def serialize_message(topic, message):
            try:
                if serializator is not None:
                    message = serializator.validated_message(message)
            except exceptions.SerializationError as se:
                error = f'topic: {topic} error: {str(se)}'
                return {'success':False, 'error':error}
            except Exception as e:
                raise SerializationError(e)
            return message

        def wrapper(topic, message):
            message = serialize_message(topic, message)
            return function(topic, message)

        async def wrapper_async(topic, message):
            message = serialize_message(topic, message)
            return await function(topic, message)

        if asyncio.iscoroutinefunction(function):
            return wrapper_async
        else:
            return wrapper

    @staticmethod
    def _check_subscription(subsciption):
        if not subsciption in _EventManager.SUBSCRIPTIONS:
            _EventManager.SUBSCRIPTIONS[subsciption] = []


class _TaskManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """
    TASKS = []

    @staticmethod
    def task(**kwargs):
        def wrapper(task):
            _TaskManager._check_task(task)
            _TaskManager.TASKS.append(task)
            return task
        return wrapper

    @staticmethod
    def _check_task(task):
        #TODO
        pass


class _IntervalTaskManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """
    INTERVAL_TASKS = {}

    @staticmethod
    def timer_task(interval: float or int):
        def wrapper(interval_task: Callable):
            _IntervalTaskManager._check_timer_task(interval, interval_task)
            if asyncio.iscoroutinefunction(interval_task):
                interval_task = _IntervalTaskManager.wrap_coro_by_interval(interval, interval_task)
            else:
                interval_task = _IntervalTaskManager.wrap_function_by_interval(interval, interval_task)
            if not interval in _IntervalTaskManager.INTERVAL_TASKS:
                _IntervalTaskManager.INTERVAL_TASKS[interval] = []
            _IntervalTaskManager.INTERVAL_TASKS[interval].append(interval_task)
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