import asyncio
import logging
import os
from dotenv import load_dotenv
from utils.binance.futures import Futures, FuturesWebsocketAsync

load_dotenv('.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def place_limit_order(client,symbol: str, quantity: float, price: float):
    side = 'BUY'
    order_type = 'MARKET'
    time_in_force = 'GTC'
    position_side = 'BOTH'
    new_order_resp_type = 'RESULT'

    try:
        response = client.new_order(
                symbol = symbol,
                side = side,
                type = order_type,
                quantity = quantity,
                price = price,
                timeInForce = time_in_force,
                posotionSide = position_side,
                newOrderResp = new_order_resp_type
                )
        logging.info(f'Limit Buy Order Was Placed Succsefuly:{response}')
    except Exception as e:
        logging.info(f'Error placing buy order for {symbol}: {e}')


async def run_trader():

    api_key = os.getenv("BINANCE_PUBLIC_KEY")
    secret_key = os.getenv("BINANCE_SECRET_KEY")

    if not api_key or not secret_key:
        logging.warning('Api Key or Secret key is not found')
        return

    futures_client = Futures(api_key=api_key,secret_key=secret_key,asynced=True,testnet=True)


    previous_candle_close_price = None


    async def on_message(ws, msg):
        nonlocal previous_candle_close_price

        logging.info(f'Recived: {msg}')
        data = msg


        if data.get('e') == 'kline' and data.get('s') == 'BTCUSDT':
            kline_data = data.get('k',{})
            curr_pr_str = kline_data.get('c')
            is_candle_closed = kline_data.get('x', False)

            if curr_pr_str is None:
                logging.warning('Current price (C) is None')
                return

            current_price = float(curr_pr_str)
            logging.info(f'BTCUSDT Kline: Close={current_price}, Is Closed = {is_candle_closed}')

            if is_candle_closed:
                logging.info(f'Candle Closed. Prev Close: {previous_candle_close_price}, New Close: {current_price}')
                previous_candle_close_price = current_price
            else:
                if previous_candle_close_price is not None:
                    price_diff = current_price - previous_candle_close_price
                    logging.info(f'Price Upd: Current: {current_price}, Prev Close: {previous_candle_close_price}, Diff: {price_diff}')

                    if price_diff >= 30:
                        logging.info(f'Price Incresed for 30 or more {price_diff}. Current Price: {current_price}, Prev Price: {previous_candle_close_price}. Triggering Buy Order')
                        asyncio.create_task(place_limit_order(futures_client,'BTCUSDT',0.003,current_price))

                else:
                    logging.info(f'Price Upd: Current: {current_price}, Prev Price: {previous_candle_close_price}. Waiting for first candle to make the order')


    ws = FuturesWebsocketAsync(stream=['btcusdt@kline_1m'], on_message=on_message,testnet=True)

    logging.info('Websocket Connection has started')


    asyncio.create_task(ws.run())

    logging.info('Websocket task create. Run trader will keep alive to allow WebSocket to operate')

    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(run_trader())
    except KeyboardInterrupt:
        logging.info('Trader application Stoped Manualy')
    except Exception as e:
        logging.Error(f'Unhandled exception in trader application: {e}', exc_info = True)
