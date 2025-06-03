import asyncio
import hmac
import json
import time
from datetime import datetime
from .base_ws_user_data import BaseWsUserData
import websockets
import logging
from utils.functions import send_to_telegram
from config import BYBIT_API_KEY, BYBIT_SECRET_KEY, TEST_API_KEY, TEST_SECRET_KEY, TEST_MODE
if TEST_MODE:
    api_key = TEST_API_KEY
    secret_key = TEST_SECRET_KEY
else:
    api_key = BYBIT_API_KEY
    secret_key = BYBIT_SECRET_KEY

logger = logging.getLogger(__name__)


class BybitWsUserData(BaseWsUserData):
    def __init__(self, rebalancer, client, symbol_settings, tg_queue, shutdown_event, handler=None):
        super().__init__(api_key, secret_key, rebalancer, client, shutdown_event, handler=handler)
        print(f"Initialization of Websocket class... Test mode: {TEST_MODE}")
        self.url = "wss://stream-demo.bybit.com/v5/private" if TEST_MODE else "wss://stream.bybit.com/v5/private"
        self.pause_time = 2
        # self.url = "wss://stream-demo.bybit.com/v5/private"  # Demo
        self.ready_event = asyncio.Event()
        self.api_key = api_key
        self.secret_key = secret_key
        self.rebalancer = rebalancer
        self.client = client
        self.symbol_settings = symbol_settings
        self.tg_queue = tg_queue
        self.topics = ['order.spot', 'wallet']
        self.handler = handler or self.on_message
        self.ws = None
        self.is_connected = False
        self.keep_alive_task = None
        self.shutdown_event: asyncio.Event = shutdown_event
        self.buy_last_qty = 0
        self.buy_last_amount = 0
        self.sell_last_qty = 0
        self.sell_last_amount = 0
        self.last_message_time = {}
        self.asset_available = 0
        self.base_asset_name = self.client.symbol_info[self.symbol_settings.symbol].base_asset

    def socket_signature(self, expires):
        return str(hmac.new(bytes(self.secret_key, "utf-8"), bytes(f"GET/realtime{expires}", "utf-8"),
                            digestmod="sha256").hexdigest())

    async def connect(self):
        while not self.shutdown_event.is_set():
            try:
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
                    self.is_connected = True
                    await self.on_open()
                    self.keep_alive_task = asyncio.create_task(self.keep_alive())
                    async for message in ws:
                        try:
                            await self.handler(message)
                        except Exception:
                            logger.exception("Exception in handler")
                            break
            except asyncio.CancelledError:
                logger.info('Connection was closed - CancelledError')
                self.is_connected = False
                break
            except Exception as e:
                logger.exception('Connection error')
                self.is_connected = False
                await self.on_error(e)
                await asyncio.sleep(1)


    async def on_open(self):
        logger.info('WsUserData was opened!')
        expires = int((time.time() + 2) * 1000)
        auth_topics = [self.api_key, expires, self.socket_signature(expires)]
        await self.auth_websocket_on_open(auth_topics)

    async def on_error(self, error):
        logger.error("On Error:", exc_info=(type(error), error, error.__traceback__))

    async def on_close(self, ws, status, msg):
        logger.info("Time:", datetime.now(), 'on_close', ws, status, msg)
        self.is_connected = False

    async def on_message(self, msg):
        try:
            data = json.loads(msg)
            # logger.debug(data)
            if 'op' in data and data.get('op') == 'auth' and data['success']:
                logger.info("Auth successfully")
                await self.subscribe_to_topics(self.topics)
            if 'success' in data and data['success'] and data.get('op') == 'subscribe':
                print("Subscription successful")
                self.ready_event.set()
            if 'topic' in data and data.get('topic') == 'wallet':
                coins = data['data'][0]['coin']
                for coin in coins:
                    if coin['coin'] == self.base_asset_name:
                        self.asset_available = float(coin['availableToWithdraw'])
                        break
            if 'topic' in data and data.get('topic') == 'order.spot':
                reply_result = None
                data = data['data'][0]
                symbol = data['symbol']
                if not self.symbol_settings or self.symbol_settings.symbol != symbol:
                    return
                current_time = datetime.now()
                if data['orderType'] == 'Limit' and data['orderStatus'] in ('Filled', 'PartiallyFilled'):
                    print("Verify trading mode ==>>", self.symbol_settings.trade_mode)
                    entry_price = float(data['price'])
                    filled_side = data['side']
                    cumulative_qty = float(data['cumExecQty'])
                    cumulative_amount = float(data['cumExecValue'])
                    average_price = float(data['avgPrice'])
                    if filled_side == 'Buy':
                        executed_qty = cumulative_qty - self.buy_last_qty
                        quoted_amount = cumulative_amount - self.buy_last_amount
                        self.buy_last_amount = cumulative_amount
                        self.buy_last_qty = cumulative_qty
                    else:
                        executed_qty = cumulative_qty - self.sell_last_qty
                        quoted_amount = cumulative_amount - self.sell_last_amount
                        self.sell_last_amount = cumulative_amount
                        self.sell_last_qty = cumulative_qty
                    logger.debug(
                        f"Executed Order: ==>> price: {data['price']} // {data['side']} // Quantity: {data['cumExecQty']}\n"
                        f"EXECUTED: {executed_qty} // AMOUNT: {quoted_amount}")

                    if executed_qty > 0:
                        if filled_side == 'Buy':
                            await self.rebalancer.update_portfolio(executed_qty, -quoted_amount, entry_price)
                            print(f"Portfolio Updated from BUY: {executed_qty, -quoted_amount, entry_price}")
                        else:
                            await self.rebalancer.update_portfolio(-executed_qty, quoted_amount, entry_price)
                            print(f"Portfolio Updated from SELL: {-executed_qty, quoted_amount, entry_price}")
                    # до этого момента обработали данные по выполненному ордеру и имеем фактические изменения
                    # executed_qty и quoted_amount которые могут быть отрицательными или положительными

                    if data['orderStatus'] == 'Filled':
                        # обнуляем временные переменные (особенность байбита)
                        if filled_side == 'Buy':
                            self.buy_last_qty = 0
                            self.buy_last_amount = 0
                        else:
                            self.sell_last_qty = 0
                            self.sell_last_amount = 0
                        # Если мы в активной торговле, выполняем действия после закрытия ордера
                        if self.symbol_settings.trade_mode == 2:
                            await self.rebalancer.update_after_pair_filled()
                        # Если мы набираем/сбрасываем ассет
                        else:
                            # При разных ценах пробуем выполнить ордер на остаток обьема (если достаточно)
                            if average_price and average_price != entry_price:
                                print("Average price: ", average_price, "/// Entry price: ", entry_price)
                                self.rebalancer.order_id = None
                                finish = await self.rebalancer.activation_price_differ()
                                # reply_result = await self.not_filled_message()
                                reply_result = await self.rebalancer.not_filled_message()
                                # await send_to_telegram(reply_result)
                                # если не полностью выполнен обьем, прерываем дальнейшее исполнение
                                # финиш выйдет при недостатке обьема на один минимальный ордер или
                                # при выявлении, что запланированный обьем уже равен или больше выполненного
                                if not finish:
                                    logger.info(f"Not fully executed order: {reply_result}")
                                    return
                            self.rebalancer.order_id = None
                            logger.info(f"Liquidity change for {symbol} completed!")
                            await self.rebalancer.clear_investment()
                            reply_result = await self.rebalancer.filled_message()
                            # self.rebalancer.invest_planned = 0
                            # self.rebalancer.last_investment = 0
                            # logger.info(f"Filled message: {reply_result}")
                            # await send_to_telegram(reply_result)
                            self.symbol_settings.trade_mode = 2
                            self.symbol_settings.investment = 0
                            await self.tg_queue.put('reload_config')
                            self.rebalancer.create_orders()
                            await self.rebalancer.place_orders()
                    else:
                        if self.symbol_settings.trade_mode == 1:
                            time_since_last_message = (
                                    current_time - self.last_message_time.get(symbol, datetime.min)).total_seconds()
                            if time_since_last_message >= 2:
                                reply_result = await self.rebalancer.not_filled_message()
                                self.last_message_time[symbol] = current_time
                            else:
                                logger.debug(f"Message for {symbol} skipped due to rate limit.")
                        # else:
                        #     reply_result = await self.rebalancer.not_filled_message()

                    if reply_result:
                        await send_to_telegram(reply_result)

        except Exception:
            logger.exception("Exception in on_message")

    async def auth_websocket_on_open(self, auth_topics):
        if self.is_connected:
            data = {"op": "auth", "args": auth_topics}
            await self.ws.send(json.dumps(data))

    async def subscribe_to_topics(self, topics):
        if topics and self.is_connected:
            data = {"op": "subscribe", "args": topics}
            await self.ws.send(json.dumps(data))

    async def unsubscribe_from_topics(self, topics):
        if topics and self.is_connected:
            data = {"op": "unsubscribe", "args": topics}
            await self.ws.send(json.dumps(data))

    async def disconnect(self):
        if self.is_connected:
            await self.ws.close()
            self.is_connected = False
            logger.info("Disconnected WebSocket")

    async def keep_alive(self):
        while self.is_connected:
            try:
                await asyncio.sleep(300)
                if self.is_connected:
                    data = {"op": "ping"}
                    await self.ws.send(json.dumps(data))
            except asyncio.CancelledError:
                logger.exception('Keep-alive was cancelled')
                break
            except Exception:
                logger.exception('Keep-alive error')
                self.is_connected = False
                break

