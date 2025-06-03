import asyncio
import hmac
import json
import time
from datetime import datetime
from .base_ws_user_data import BaseWsUserData
from websockets.exceptions import ConnectionClosedError
import websockets
import logging
from utils.functions import send_to_telegram
from config import CRYPTOCOM_API_KEY, CRYPTOCOM_SECRET_KEY, TEST_API_KEY, TEST_SECRET_KEY, TEST_MODE
if TEST_MODE:
    api_key = TEST_API_KEY
    secret_key = TEST_SECRET_KEY
else:
    api_key = CRYPTOCOM_API_KEY
    secret_key = CRYPTOCOM_SECRET_KEY

logger = logging.getLogger(__name__)


class CryptocomWsUserData(BaseWsUserData):
    def __init__(self, rebalancer, client, symbol_settings, tg_queue, shutdown_event, handler=None):
        super().__init__(api_key, secret_key, rebalancer, client, shutdown_event, handler=handler)
        self.url = "wss://stream.crypto.com/exchange/v1/user"
        self.pause_time = 4
        self.ready_event = asyncio.Event()
        self.api_key = api_key
        self.secret_key = secret_key
        self.rebalancer = rebalancer
        self.client = client
        self.symbol_settings = symbol_settings
        self.tg_queue = tg_queue
        self.topics = [f"user.order.{symbol_settings.symbol}", "user.balance"]
        self.handler = handler or self.on_message
        self.ws = None
        self.is_connected = False
        self.keep_alive_task = None
        self.shutdown_event = shutdown_event or asyncio.Event()
        self.sub_id = 10000001
        self.auth_id = 0
        self.heartbit_id = None
        self.buy_last_qty = 0
        self.buy_last_amount = 0
        self.sell_last_qty = 0
        self.sell_last_amount = 0
        self.last_message_time = {}
        self.first_message = True
        self.asset_available = 0
        self.base_asset_name = self.client.symbol_info[self.symbol_settings.symbol].base_asset
        print("==<<<>>>", self.base_asset_name)
        # self.base_asset_name = self.client.symbol_info[self.symbol_settings.symbol].base_asset

    def socket_signature(self, expires):
        return str(hmac.new(bytes(self.secret_key, "utf-8"), bytes(f"GET/realtime{expires}", "utf-8"),
                            digestmod="sha256").hexdigest())

    async def connect(self):
        while not self.shutdown_event.is_set():
            try:
                async with websockets.connect(self.url, ping_interval=15, ping_timeout=10) as ws:
                    self.ws = ws
                    self.is_connected = True
                    await self.on_open()
                    # self.keep_alive_task = asyncio.create_task(self.keep_alive())
                    async for message in ws:
                        try:
                            await self.handler(message)
                        except Exception:
                            logger.exception("Exception in handler")
                            break
            except ConnectionClosedError as cce:
                # Это ожидаемое событие: соединение просто было закрыто без корректного close frame
                logger.warning("Websocket connection closed unexpectedly: %s", cce)
                self.is_connected = False
                # Можем сделать небольшую задержку и переподключиться
                await asyncio.sleep(1)
                continue
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
        logger.info('Websocket was opened!')
        await asyncio.sleep(1)
        endpoint = "public/auth"
        req = await self.client.request(endpoint=endpoint, params={}, ws_call=True)
        await self.auth_websocket_on_open(req)

    async def on_error(self, error):
        logger.error("On Error:", exc_info=(type(error), error, error.__traceback__))

    async def on_close(self, ws, status, msg):
        logger.info("Time:", datetime.now(), 'on_close', ws, status, msg)
        self.is_connected = False

    async def on_message(self, msg):
        order_data = None
        try:
            raw_data = json.loads(msg)
            # logger.debug(raw_data)
            if 'method' not in raw_data:
                return
            if 'code' in raw_data and raw_data['code'] != 0:
                raise Exception("DEBUG ERROR: ", raw_data['code'], raw_data)
            if raw_data.get('method') == 'public/auth':
                logger.info("Auth successfully")
                await self.subscribe_to_topics(self.topics)
                return
            if raw_data.get('method') == 'public/heartbeat':
                self.heartbit_id = raw_data['id']
                response_beat = {"id": self.heartbit_id, "method": "public/respond-heartbeat"}
                await self.ws.send(json.dumps(response_beat))
                return
            if raw_data.get('method') == 'subscribe':
                if raw_data['id'] == self.sub_id:
                    print("Subscription successfully!")
                    self.ready_event.set()
                    return
                else:
                    if raw_data.get('result') and 'data' in raw_data['result'] and len(raw_data['result']['data']) > 0:
                        if raw_data['result']['channel'] == "user.order":
                            order_data = raw_data['result']['data'][0]
                            logger.debug(order_data)
                            if not order_data:
                                return
                            #>>> continue if order_data get value...>>>

                        elif raw_data['result']['channel'] == "user.balance":
                            balance_data = raw_data['result']['data'][0]['position_balances']
                            for el in balance_data:
                                if el['instrument_name'] == self.base_asset_name:
                                    self.asset_available = float(el['max_withdrawal_balance'])
                                    return
                        else:
                            return
                    else:
                        return

                # For order_data passed...
                if self.first_message:
                    self.first_message = False
                    return

                reply_result = None
                symbol = order_data['instrument_name']
                if not self.symbol_settings or self.symbol_settings.symbol != symbol:
                    return
                current_time = datetime.now()
                if order_data['order_type'] == 'LIMIT' and order_data['status'] in ('FILLED', 'ACTIVE'):
                    print("Verify trading mode ==>>", self.symbol_settings.trade_mode)
                    entry_price = float(order_data['limit_price'])
                    filled_side = order_data['side']
                    cumulative_qty = float(order_data['cumulative_quantity'])
                    if cumulative_qty == 0:
                        logger.debug(f"Limit Order NEW Listed! <><><> (Not partly filled...)")
                        return
                    cumulative_amount = float(order_data['cumulative_value'])
                    average_price = float(order_data['avg_price'])
                    if filled_side == 'BUY':
                        executed_qty = cumulative_qty - self.buy_last_qty
                        quoted_amount = cumulative_amount - self.buy_last_amount
                        self.buy_last_qty = cumulative_qty
                        self.buy_last_amount = cumulative_amount
                    else:
                        executed_qty = cumulative_qty - self.sell_last_qty
                        quoted_amount = cumulative_amount - self.sell_last_amount
                        self.sell_last_amount = cumulative_amount
                        self.sell_last_qty = cumulative_qty
                    logger.debug(
                        f"Executed Order: ==>> price: {order_data['limit_price']} // {order_data['side']} // Quantity: {cumulative_qty}\n"
                        f"EXECUTED: {executed_qty} // AMOUNT: {quoted_amount}")

                    if executed_qty > 0:
                        if filled_side == 'BUY':
                            await self.rebalancer.update_portfolio(executed_qty, -quoted_amount, entry_price)
                            print(f"Portfolio Updated from BUY: {executed_qty, -quoted_amount, entry_price}")
                        else:
                            await self.rebalancer.update_portfolio(-executed_qty, quoted_amount, entry_price)
                            print(f"Portfolio Updated from SELL: {-executed_qty, quoted_amount, entry_price}")
                    # до этого момента обработали данные по выполненному ордеру и имеем фактические изменения
                    # executed_qty и quoted_amount которые могут быть отрицательными или положительными

                    if order_data['status'] == 'FILLED':
                        # обнуляем временные переменные (особенность байбита)
                        if filled_side == 'BUY':
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

    async def auth_websocket_on_open(self, auth_req):
        if self.is_connected:
            self.auth_id = auth_req['id']
            await self.ws.send(json.dumps(auth_req))

    async def subscribe_to_topics(self, topics):
        params = {"channels": topics}
        if topics and self.is_connected:
            data = {"id": self.sub_id,
                    "method": "subscribe",
                    "params": params,
                    "nonce": int(time.time() * 1000)}
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

    # async def keep_alive(self):
    #     while self.is_connected:
    #         try:
    #             await asyncio.sleep(15)
    #             if self.is_connected:
    #                 if self.heartbit_id:
    #                     data = {"id": self.heartbit_id,
    #                             "method": "public/respond-heartbeat"}
    #                     await self.ws.send(json.dumps(data))
    #         except asyncio.CancelledError:
    #             logger.exception('Keep-alive was cancelled')
    #             break
    #         except Exception:
    #             logger.exception('Keep-alive error')
    #             self.is_connected = False
    #             break

