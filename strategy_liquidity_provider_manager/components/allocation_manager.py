import sys
import traceback

import pandas as pd

from anthill.logger.logger import Logger

log = Logger(name='allocation_manager').log


class AllocationManager:
    """
     Calculate the allocation between all the registered bots

    """
    def __init__(self, balance_manager, config):
        self._config = config
        # self._bots = pd.DataFrame(self._config.bots)
        # self._bots.index = self._bots["name"]
        self._weight_map = None

        self._balance_manager = balance_manager

        self._remaining_balance = None
        self._total_balance = None

        columns = ["target_first", "target_second", "base_first", "base_second"]

        self._bots_balance_percent = pd.DataFrame(columns=columns)
        self._bots_balance_amount = pd.DataFrame(columns=columns)

    @property
    def allocations(self):
        return self._bots_balance_percent

    def calculate(self):
        try:
            self._reset()
            balance_summary = self._remaining_balance.sum(axis=1)
            if balance_summary.empty or not balance_summary.all():
                return
            while not self._is_balance_filled():
                self._fill_lowest_node()
                self._fill_opposite_nodes()
        except Exception as ex:
            log("\n".join(traceback.format_exception(
                sys.exc_info()[0],
                sys.exc_info()[1],
                sys.exc_info()[2]
            )))

    def _reset(self):
        # reset balance
        self._remaining_balance = self._balance_manager.allocated_total_balance()
        self._total_balance = self._balance_manager.total_balance()

        self._bots_balance_percent *= pd.np.NaN
        self._bots_balance_amount *= pd.np.NaN

        # reset weights
        self._weight_map = self._balance_manager.balance_map()
        for bot_name, bot in self._bots.iterrows():
            for spot in ("target", "base"):
                exchange_key = "_".join((spot, "exchange"))
                account_key = "_".join((spot, "account"))
                symbol_key = "_".join((spot, "symbol"))

                exchange = bot[exchange_key]
                account = bot[account_key]
                symbol = bot[symbol_key]

                first_currency, second_currency = symbol.split("/")
                coefficient = bot["weight"]

                self._weight_map[first_currency][(exchange, account)] += coefficient
                self._weight_map[second_currency][(exchange, account)] += coefficient

    def _is_balance_filled(self) -> bool:
        return not self._bots_balance_percent.isna().any().any()

    def _fill_lowest_node(self):
        # init minimal balance
        min_balance = self._total_balance.sum().sum()

        # selected parameters
        selected_bot_name = None
        selected_column = None
        selected_exchange = None
        selected_account = None
        selected_currency = None

        # go through all spots and select with the lowest balance
        for bot_name, bot in self._bots.iterrows():
            for column in self._bots_balance_percent.columns:
                if pd.notna(self._bots_balance_percent[column][bot_name]):
                    continue

                spot, spot_currency = column.split("_")
                exchange = bot[spot + "_exchange"]
                account = bot[spot + "_account"]
                symbol = bot[spot + "_symbol"]

                if spot_currency == "first":
                    currency = symbol.split("/")[0]
                else:
                    currency = symbol.split("/")[1]

                init_coefficient = bot["weight"]
                total = self._weight_map[currency][(exchange, account)]
                coefficient = init_coefficient / total
                allocation = self._remaining_balance[currency][(exchange, account)] * coefficient

                # select minimum balance
                if allocation < min_balance:
                    selected_bot_name = bot_name
                    selected_column = column
                    selected_currency = currency
                    selected_exchange = exchange
                    selected_account = account
                    min_balance = allocation

        # apply selected spot
        # if not selected_bot_name:
            # log(selected_bot_name, "selected_bot_name")

        coefficient = self._bots["weight"][selected_bot_name]
        total_balance = self._total_balance[selected_currency][(selected_exchange, selected_account)]
        amount = min_balance
        percent = min_balance / total_balance
        if pd.isna(percent):
            percent = 0.0
        self._bots_balance_amount[selected_column][selected_bot_name] = amount
        self._bots_balance_percent[selected_column][selected_bot_name] = percent
        self._remaining_balance[selected_currency][(selected_exchange, selected_account)] -= min_balance
        self._weight_map[selected_currency][(selected_exchange, selected_account)] -= coefficient

    def _fill_opposite_nodes(self):
        filled = False
        for bot_name, bot in self._bots.iterrows():
            bot_balance_percent = self._bots_balance_percent.loc[bot_name]
            bot_balance_amount = self._bots_balance_amount.loc[bot_name]
            for (column, opposite_column) in (("target_first", "base_second"),
                                              ("target_second", "base_first"),
                                              ("base_first", "target_second"),
                                              ("base_second", "target_first")):

                if pd.isna(bot_balance_amount[column]) or pd.notna(bot_balance_amount[opposite_column]):
                    continue

                spot, spot_currency = opposite_column.split("_")
                amount = bot_balance_amount[column]
                exchange = bot[spot + "_exchange"]
                account = bot[spot + "_account"]
                symbol = bot[spot + "_symbol"]

                if spot_currency == "first":
                    currency = symbol.split("/")[0]
                else:
                    currency = symbol.split("/")[1]

                weight = bot["weight"]

                total_balance = self._total_balance[currency][(exchange, account)]
                bot_balance_amount[opposite_column] = amount
                bot_balance_percent[opposite_column] = amount / total_balance

                self._remaining_balance[currency][(exchange, account)] -= amount
                self._weight_map[currency][(exchange, account)] -= weight

                filled = True
                break
            if filled:
                break
