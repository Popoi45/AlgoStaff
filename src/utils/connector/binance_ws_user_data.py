import asyncio
import json
import time
import traceback
from datetime import datetime
from .base_ws_user_data import BaseWsUserData
import websockets
import logging
import aiohttp
from utils import db
from utils.functions import send_to_telegram
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, TEST_MODE, TEST_API_KEY, TEST_SECRET_KEY

if TEST_MODE:
    api_key = TEST_API_KEY
    secret_key = TEST_SECRET_KEY
    base_url = "https://testnet.binance.vision"
    ws_base_url = "wss://stream.testnet.binance.vision:9443/ws"
else:
    api_key = BINANCE_API_KEY
    secret_key = BINANCE_SECRET_KEY
    base_url = "https://api.binance.com"
    ws_base_url = "wss://stream.binance.com:9443/ws"

logger = logging.getLogger(__name__)

class BinanceWsUserData(BaseWsUserData):
    def __init__(self, rebalancer, client, symbol_settings, tg_queue, shutdown_event, handler=None):
        super().__init__(api_key, secret_key, rebalancer, client, shutdown_event, handler=handler)
        print(f"Initialization of Binance WebSocket class... Test mode: {TEST_MODE}")
        self.ready_event = asyncio.Event()
        self.base_url = base_url
        self.ws_base_url = ws_base_url
        self.pause_time = 2
        self.api_key = api_key
        self.secret_key = secret_key
        self.rebalancer = rebalancer
        self.client = client
        self.symbol_settings = symbol_settings
        self.tg_queue = tg_queue
        self.handler = handler or self.on_message
        self.ws = None
        self.is_connected = False
        self.keep_alive_task = None
        self.shutdown_event: asyncio.Event = shutdown_event
        self.listen_key = None
        self.keep_alive_interval = 60 * 20  # 20 minutes
        self.last_message_time = {}
        self.asset_available = 0
        self.base_asset_name = self.client.symbol_info[self.symbol_settings.symbol].base_asset


    async def get_listen_key(self):
        endpoint = "/api/v3/userDataStream"
        headers = {"X-MBX-APIKEY": self.api_key}
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url + endpoint, headers=headers) as response:
                data = await response.json()
                if response.status != 200:
                    raise Exception(f"Error obtaining listenKey: {data['msg']}")
                self.listen_key = data['listenKey']
                logger.info(f"Obtained listenKey: {self.listen_key}")

    async def keep_alive_listen_key(self):
        while self.is_connected:
            try:
                await asyncio.sleep(self.keep_alive_interval)
                endpoint = "/api/v3/userDataStream"
                headers = {"X-MBX-APIKEY": self.api_key}
                params = {"listenKey": self.listen_key}
                async with aiohttp.ClientSession() as session:
                    async with session.put(self.base_url + endpoint, params=params, headers=headers) as response:
                        if response.status != 200:
                            data = await response.json()
                            logger.error(f"Failed to keep alive listenKey: {data}")
                        else:
                            logger.info("Successfully kept alive listenKey")
            except asyncio.CancelledError:
                logger.info("Keep-alive task cancelled")
                break
            except Exception:
                logger.exception("Exception in keep_alive_listen_key")
                break

    async def connect(self):
        while not self.shutdown_event.is_set():
            try:
                await self.get_listen_key()
                ws_url = f"{self.ws_base_url}/{self.listen_key}"
                async with websockets.connect(ws_url) as ws:
                    self.ws = ws
                    self.is_connected = True
                    await self.on_open()
                    self.keep_alive_task = asyncio.create_task(self.keep_alive_listen_key())
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
        logger.info('WebSocket connection opened')
        self.ready_event.set()
        # No authentication needed as listenKey handles it

    async def on_error(self, error):
        logger.error("On Error:", exc_info=(type(error), error, error.__traceback__))

    async def on_close(self, ws, status, msg):
        logger.info("WebSocket connection closed")
        self.is_connected = False

    async def on_message(self, msg):
        try:
            data = json.loads(msg)
            event_type = data.get('e')
            if event_type == 'executionReport':
                await self.handle_execution_report(data)
            elif event_type == 'outboundAccountPosition':
                await self.handle_account_update(data)
            else:
                logger.debug(f"Unhandled event type: {event_type}")
        except Exception:
            logger.exception("Exception in on_message")

    async def disconnect(self):
        if self.is_connected:
            await self.ws.close()
            self.is_connected = False
            logger.info("Disconnected WebSocket")

    async def handle_account_update(self, data):
        balances = data['B']
        for balance in balances:
            asset = balance['a']
            if asset == self.base_asset_name:
                self.asset_available = float(balance['f'])
                break

    async def handle_execution_report(self, data):
        print(f"Execution report: {data}")
        filled = False
        reply_result = None
        symbol = data['s']
        if not self.symbol_settings or self.symbol_settings.symbol != symbol:
            return
        current_time = datetime.now()
        order_status = data['X']
        if order_status == 'FILLED':
            filled = True
        order_type = data['o']
        if order_type == 'LIMIT' and order_status in ('FILLED', 'PARTIALLY_FILLED'):
            entry_price = float(data['p'])
            executed_qty = float(data['l'])
            quoted_amount = float(data['Y'])
            executed_price = float(data['L'])  # Last executed price
            filled_side = data['S']

            if filled_side == 'BUY':
                logger.info(f"Portfolio Updated from BUY: {executed_qty}, {-quoted_amount}, {executed_price}")
                await self.rebalancer.update_portfolio(executed_qty, -quoted_amount, executed_price)
            else:
                logger.info(f"Portfolio Updated from SELL: {-executed_qty}, {quoted_amount}, {executed_price}")
                await self.rebalancer.update_portfolio(-executed_qty, quoted_amount, executed_price)
            if filled:
                if self.symbol_settings.trade_mode == 2:
                    await self.rebalancer.update_after_pair_filled()
                else:
                    if entry_price != executed_price:
                        logger.debug("Executed price differs from entry price")
                        self.rebalancer.order_id = None
                        finish = await self.rebalancer.activation_price_differ()
                        reply_result = await self.rebalancer.not_filled_message()
                        if not finish:
                            logger.info(f"Not fully executed order: {reply_result}")
                            return
                    self.rebalancer.order_id = None
                    logger.info(f"Liquidity change for {symbol} completed!")
                    await self.rebalancer.clear_investment()
                    reply_result = await self.rebalancer.filled_message()
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
                #     # Не полное исполнение ордера в торговом режиме
                #     reply_result = await self.rebalancer.not_filled_message()

            if reply_result:
                await send_to_telegram(reply_result)
