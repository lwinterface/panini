import time
import asyncio
from . import exceptions
from typing import Callable
from .exceptions import (
    ValidationError,
    InitializingIntervalTaskError,
    NotReadyError,
    BaseError,
)


class _EventManager:
    """
    Collect all functions from each module wrapped by @app.subscription or @EventManager.subscribe
    """

    SUBSCRIPTIONS = {}

    def listen(
        self, subject: list or str, validator: type = None, dynamic_subscription=False
    ):
        def wrapper(function):
            function = _EventManager.wrap_function_by_validator(function, validator)
            if type(subject) is list:
                for t in subject:
                    _EventManager._check_subscription(t)
                    _EventManager.SUBSCRIPTIONS[t].append(function)
            else:
                _EventManager._check_subscription(subject)
                _EventManager.SUBSCRIPTIONS[subject].append(function)
            return function

        if dynamic_subscription:
            if type(subject) is list:
                for s in subject:
                    self._subscribe(s, wrapper)
            else:
                self._subscribe(subject, wrapper)
        return wrapper

    def _subscribe(self, subject, function):
        if not hasattr(self, "connector") or self.connector.check_connection is False:
            raise NotReadyError(
                "Something wrong. NATS client should be connected first"
            )
        self.subscribe_new_subject(subject, function)

    @staticmethod
    def wrap_function_by_validator(function, validator):
        def validate_message(subject, message):
            try:
                if validator is not None:
                    message = validator.validated_message(message)
            except exceptions.ValidationError as se:
                error = f"subject: {subject} error: {str(se)}"
                return {"success": False, "error": error}
            except Exception as e:
                raise ValidationError(e)
            return message

        def wrapper(subject, message):
            message = validate_message(subject, message)
            return function(subject, message)

        async def wrapper_async(subject, message):
            message = validate_message(subject, message)
            return await function(subject, message)

        if asyncio.iscoroutinefunction(function):
            return wrapper_async
        else:
            return wrapper

    @staticmethod
    def _check_subscription(subscription):
        if subscription not in _EventManager.SUBSCRIPTIONS:
            _EventManager.SUBSCRIPTIONS[subscription] = []


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
        # TODO
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
                interval_task = _IntervalTaskManager.wrap_coro_by_interval(
                    interval, interval_task
                )
            else:
                interval_task = _IntervalTaskManager.wrap_function_by_interval(
                    interval, interval_task
                )
            if interval not in _IntervalTaskManager.INTERVAL_TASKS:
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
                except InitializingIntervalTaskError as e:
                    # TODO: warning log
                    pass

        return wrapper

    @staticmethod
    def wrap_function_by_interval(interval, interval_task):
        def wrapper(**kwargs):
            while True:
                try:
                    interval_task(**kwargs)
                    time.sleep(interval)
                except InitializingIntervalTaskError as e:
                    # TODO: warning log
                    pass

        return wrapper

    @staticmethod
    def _check_timer_task(interval, interval_task):
        # TODO
        pass
