import json

import pandas as pd

from anthill.logger.logger import Logger

log = Logger(name='balance_manager').log


class BalanceManager:

    def __init__(self, config):
        self._config = config

        self._price_map = pd.DataFrame()

        self._total_normalized_balances = pd.DataFrame()
        self._free_normalized_balances = pd.DataFrame()

        self._total_balances = pd.DataFrame()
        self._free_balances = pd.DataFrame()

    def on_balance_update(self, topic, message):
        log(f"on_balance_update {topic}")

        source, service, exchange, symbol, account, endpoint = topic.split(".")
        message = json.loads(message)

        for currency, value in message.items():
            self._total_balances.at[(exchange, account), currency] = value["total"]
            self._free_balances.at[(exchange, account), currency] = value["free"]

            log(self._total_balances)

        self._calculate_normalized_balance()

    def on_price_update(self, topic, message):
        log(f"on_price_update {topic}")
        source, service, exchange, sym, endpoint = topic.split(".")
        message = json.loads(message)

        for symbol, value in message.items():
            price = value["close"]
            first, second = symbol.split("/")

            # init same
            self._price_map.at[first, first] = 1.0
            self._price_map.at[second, second] = 1.0

            # init base prices
            self._price_map.at[second, first] = 1.0 / price
            self._price_map.at[first, second] = price

        self._calculate_normalized_balance()

    def _calculate_normalized_balance(self):
        if not self.is_inited():
            log(f"balance manager is not inited")
            return
        prices = self._price_map[self._config.base_currency]
        self._total_normalized_balances = self._total_balances * prices
        self._free_normalized_balances = self._free_balances * prices

    def total_balance(self):
        return self._total_normalized_balances  # .fillna(0) # only to test

    def free_balance(self):
        return self._free_normalized_balances  # .fillna(0) # only to test

    def allocated_total_balance(self):
        return self.total_balance() * self._config.balance_factor

    def allocated_free_balance(self):
        return self.free_balance() * self._config.balance_factor

    def balance_map(self):
        return self._balance_handler.total_balances().multiply(0).fillna(0)

    def is_inited(self):
        return self._price_handler.is_inited() and self._balance_handler.is_inited()
