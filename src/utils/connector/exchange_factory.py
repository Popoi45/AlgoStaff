# exchange_factory.py - async version

def get_api_instance(exchange, async_mode=True):
    exchange = exchange.lower()
    if exchange == 'bybit':
        if async_mode:
            from .bybit_api import BybitApiAsync
            return BybitApiAsync()
        elif not async_mode:
            from .bybit_api import BybitApi

    elif exchange == 'cryptocom':
        if async_mode:
            from .cryptocom_api import CryptocomApiAsync  # Ensure this class is async
            return CryptocomApiAsync()

    elif exchange == 'binance':
        if async_mode:
            from .binance_api import BinanceApiAsync
            return BinanceApiAsync()

    else:
        raise ValueError(f"Unsupported exchange: {exchange}")



def get_ws_user_data_instance(exchange, rebalancer, client, symbol_settings, tg_queue, shutdown,
                              handler=None, async_mode=True):
    exchange = exchange.lower()
    if exchange == 'bybit':
        if async_mode:
            from .bybit_ws_user_data import BybitWsUserData
            return BybitWsUserData(rebalancer, client=client, symbol_settings=symbol_settings,
                                   tg_queue=tg_queue, shutdown_event=shutdown, handler=handler)

    elif exchange == 'cryptocom':
        if async_mode:
            from .cryptocom_ws_user_data import CryptocomWsUserData
            return CryptocomWsUserData(rebalancer, client=client, symbol_settings=symbol_settings,
                                     tg_queue=tg_queue, shutdown_event=shutdown, handler=handler)

    elif exchange == 'binance':
        if async_mode:
            from .binance_ws_user_data import BinanceWsUserData
            return BinanceWsUserData(rebalancer, client=client, symbol_settings=symbol_settings,
                                     tg_queue=tg_queue, shutdown_event=shutdown, handler=handler)

    else:
        raise ValueError(f"Unsupported exchange: {exchange}")


def get_ws_market_data_instance(exchange, shutdown, topics=None, handler=None, async_mode=True):
    exchange = exchange.lower()
    if exchange == 'bybit':
        if async_mode:
            from .bybit_ws import BybitWs
            return BybitWs(shutdown_event=shutdown, topics=topics, handler=handler)

    elif exchange == 'cryptocom':
        if async_mode:
            from .cryptocom_ws import CryptocomWs
            return CryptocomWs(topics=topics, shutdown_event=shutdown, handler=handler)

    elif exchange == 'binance':
        if async_mode:
            from .binance_ws import BinanceWs
            return BinanceWs(shutdown_event=shutdown, topics=topics, handler=handler)

    else:
        raise ValueError(f"Unsupported exchange: {exchange}")
