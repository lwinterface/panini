from anthill.app import App
from .allocation_manager import AllocationManager
from .balance_manager import BalanceManager


class BotManager:
    
    def __init__(self, app: App, config, data, balance_manager: BalanceManager, allocation_manager: AllocationManager):
        self._app = app

        self._balance_manager = balance_manager
        self._allocation_manager = allocation_manager

        self._data = data
        self._config = config

    async def manage(self):
        self._allocation_manager.calculate()
        for bot_name, balance_percent in self._allocation_manager.allocations.iterrows():
            message = {"balance_percent": balance_percent.to_dict()}
            topic = f"{self._config.name}.liquidity_provider.{bot_name}.update_balance_config"
            await self._app.aio_publish(message, topic)

    def register_bot(self, config: dict):
        target_exchange = config["target_exchange"]
        target_account = config["target_account"]
        target_symbol = config["target_symbol"]

        hedge_exchange = config["hedge_exchange"]
        hedge_account = config["hedge_account"]
        hedge_symbol = config["hedge_symbol"]

        target_balance_update_topic = f"*.dataprovider.{target_exchange}.*.{target_account}.balance"
        target_ticker_update_topic = f"data_connector.public.{target_exchange}.{target_symbol}.ticker"

        hedge_balance_update_topic = f"*.dataprovider.{hedge_exchange}.*.{hedge_account}.balance"
        hedge_ticker_update_topic = f"data_connector.public.{hedge_exchange}.{hedge_symbol}.ticker"

        config["target_balance_ssid"] = self._app.subscribe_topic(target_balance_update_topic,
                                                                  self._balance_manager.on_balance_update)
        config["target_ticker_ssid"] = self._app.subscribe_topic(target_ticker_update_topic,
                                                                 self._balance_manager.on_price_update)

        config["hedge_balance_ssid"] = self._app.subscribe_topic(hedge_balance_update_topic,
                                                                 self._balance_manager.on_balance_update)
        config["hedge_ticker_ssid"] = self._app.subscribe_topic(hedge_ticker_update_topic,
                                                                self._balance_manager.on_price_update)

        self._data.add_bot(config)
    
    def unregister_bot(self, bot_name):
        bot = self._data.pop_bot(bot_name)

        self._app.unsubscribe_ssid(bot["target_balance_ssid"])
        self._app.unsubscribe_ssid(bot["target_ticker_ssid"])

        self._app.unsubscribe_ssid(bot["hedge_balance_ssid"])
        self._app.unsubscribe_ssid(bot["hedge_ticker_ssid"])

    async def ping_bots(self):
        bots_to_be_unregistered = []
        for bot_name, bot in self._data.bots.items():
            try:
                topic = f"{self._config.name}.liquidity_provider.{bot_name}.ping"
                message = {"event": "ping"}
                result = await self._app.aio_publish_request(message, topic)
                print(topic, result)
                if message["event"] == "pong":
                    pass
            except Exception as ex:
                bots_to_be_unregistered.append(bot_name)

        for bot_name in bots_to_be_unregistered:
            self.unregister_bot(bot_name)
