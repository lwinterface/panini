from anthill import app as ant_app
from strategy_liquidity_provider_manager.components.allocation_manager import AllocationManager
from strategy_liquidity_provider_manager.components.manager_data import ManagerData
from strategy_liquidity_provider_manager.config import Config
from components import BalanceManager
from components import BotManager

config_data = {
    "name": "gorilla",
    "base_currency": "BTC",
    "balance_factor": 0.9,
    "weights": {
        "default": 2,
        "TESTNET_ZEBITEX": {
            "default": 0.8,
            "zebitex2_testnet": {
                "default": 0.8,
                "BTC/USDT": 0.9,
                "BTC/EUR": 0.9,
                "BTC/USD": 0.9
            },
            "andrey_volo_testnet": {
                "default": 0.8,
                "BTC/USDT": 0.9,
                "BTC/EUR": 0.9,
                "BTC/USD": 0.9
            }
        }
    }

}

config = Config()
config.set_config(config_data)

data = ManagerData()

app = ant_app.App(
    service_name='liquidity_provider_manager',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
    store=True
)


@app.listen(f'*.liquidity_provider_manager.{config.name}.register')
def register_bot(topic: str, message: dict):
    # register the bot
    print(topic, message)
    bot_manager.register_bot(message["config"])
    return {"success": True}


@app.timer_task(interval=3)
async def ping_bots():
    await bot_manager.ping_bots()


@app.timer_task(interval=5)
async def manage():
    await bot_manager.manage()


if __name__ == "__main__":
    balance_manager = BalanceManager(config)
    allocation_manager = AllocationManager(balance_manager, config)
    bot_manager = BotManager(app, config, data, balance_manager, allocation_manager)

    app.start()
