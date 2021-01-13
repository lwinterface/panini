from utils.singleton import singleton


@singleton
class Config:

    def __init__(self):
        self._config = None

        self._weights_map = {}
        self._balance_factor_map = {}

    def set_config(self, config):
        self._config = config

    @property
    def bots(self):
        return self._config["bots"]

    @property
    def balance_factor(self):
        return self._config["balance_factor"]

    @property
    def base_currency(self):
        return self._config["base_currency"]

    @property
    def name(self):
        return self._config["name"]

    @property
    def symbols(self):
        return self._symbols

    @property
    def currencies(self):
        return self._currencies



