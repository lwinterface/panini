from anthill.utils.singleton import singleton


@singleton
class ManagerData:

    def __init__(self):
        self._bots = {}

    def add_bot(self, config: dict):
        self._bots[config["bot_name"]] = config

    def pop_bot(self, bot_name):
        return self._bots.pop(bot_name)

    @property
    def bots(self):
        return self._bots
