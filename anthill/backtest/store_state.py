


class store_state: pass


class _StoreManager:
    """
    Collect all functions from each module wrapped by @app.task or @TaskManager.task
    """
    TASKS = []

    @staticmethod
    def store_state(**kwargs):
        def wrapper(store_cls):
            _StoreManager._check_task(task)
            _StoreManager.TASKS.append(task)
            return task
        return wrapper

    @staticmethod
    def _check_task(task):
        #TODO
        pass