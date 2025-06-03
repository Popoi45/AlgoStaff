import hashlib
import hmac
import time
import urllib.parse
from .base_api import BaseApi
import aiohttp
from .symbol_info import SymbolInfo
from config import BINANCE_API_KEY, BINANCE_SECRET_KEY, TEST_API_KEY, TEST_SECRET_KEY, TEST_MODE
if TEST_MODE:
    api_key = TEST_API_KEY
    secret_key = TEST_SECRET_KEY
else:
    api_key = BINANCE_API_KEY
    secret_key = BINANCE_SECRET_KEY


class BinanceApiAsync(BaseApi):

    def __init__(self):
        self.api_key = api_key
        self.secret_key = secret_key
        self.url = "https://testnet.binance.vision" if TEST_MODE else "https://api.binance.com"
        self.header = {"X-MBX-APIKEY": self.api_key}
        self.symbol_info = {}
        self.session = None  # Initialize session to None

    async def initialize(self):
        self.session = aiohttp.ClientSession()
        await self.get_symbols_info()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None  # Reset session to None

    def gen_signature(self, params):
        params_str = urllib.parse.urlencode(params)
        sign = hmac.new(bytes(self.secret_key, "utf-8"), params_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return sign

    async def get_symbols_info(self):
        self.symbol_info = {}
        endpoint = '/api/v1/exchangeInfo'
        async with self.session.get(self.url + endpoint) as response:
            data = await response.json()
            if data:
                symbols_data = data['symbols']
                for symbol_data in symbols_data:
                    symbol_info = SymbolInfo.from_binance(symbol_data)
                    self.symbol_info[symbol_data['symbol']] = symbol_info

    async def get_exchange_info(self, symbol: str = None):
        endpoint = '/api/v1/exchangeInfo'
        params = {}
        if symbol:
            params['symbol'] = symbol
        async with self.session.get(self.url + endpoint, params=params) as response:
            return await response.json()

    async def get_order_book(self, symbol: str):
        endpoint = '/api/v3/ticker/bookTicker'
        params = {'symbol': symbol}
        async with self.session.get(self.url + endpoint, params=params) as response:
            data = await response.json()
            ask_price = float(data['askPrice'])
            bid_price = float(data['bidPrice'])
            return ask_price, bid_price

    async def post_limit_order(self, symbol, side, quantity, price, reduce_only=False, rounding="down"):
        endpoint = "/api/v3/order"
        timestamp = int(time.time() * 1000)
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'quantity': float(self.round_from_size(quantity, self.symbol_info[symbol].step_size)),
            'type': 'LIMIT',
            'price': float(self.round_from_size(price, self.symbol_info[symbol].tick_size, rounding=rounding)),
            'timeInForce': 'GTC',
            'timestamp': timestamp,
        }
        if reduce_only:
            params['reduceOnly'] = reduce_only
        params['signature'] = self.gen_signature(params)
        print(f"Debug params: {params}")
        async with self.session.post(self.url + endpoint, params=params, headers=self.header) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception(f"Error posting limit order: {data['msg']}")
            return data

    async def post_cancel_order(self, symbol: str, orderId = None, origClientOrderId: str = None):
        if orderId:
            orderId = int(orderId)
        endpoint = "/api/v3/order"
        timestamp = int(time.time() * 1000)
        params = {'symbol': symbol, 'timestamp': timestamp}
        if orderId or origClientOrderId:
            if orderId:
                params['orderId'] = orderId
            if origClientOrderId:
                params['origClientOrderId'] = origClientOrderId
        params['signature'] = self.gen_signature(params)
        async with self.session.delete(self.url + endpoint, params=params, headers=self.header) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception(f"Error posting cancel order: {data['msg']}")
            return data

    async def post_cancel_all_open_orders(self, symbol: str):
        endpoint = "/api/v3/openOrders"
        timestamp = int(time.time() * 1000)
        params = {'symbol': symbol, 'timestamp': timestamp}
        params['signature'] = self.gen_signature(params)
        async with self.session.delete(self.url + endpoint, params=params, headers=self.header) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception(f"Error posting cancel all open orders: {data['msg']}")

            return data

    async def get_coins_balance(self, coin: str = None):
        endpoint = "/api/v3/account"
        params = {'timestamp': int(time.time() * 1000)}
        params['signature'] = self.gen_signature(params)
        async with self.session.get(self.url + endpoint, params=params, headers=self.header) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception(f"Error getting coins balance: {data['msg']}")
            if coin:
                for balance in data['balances']:
                    if balance['asset'] == coin:
                        coin_balance = float(balance['free'])
                        return coin_balance
            else:
                return data
        return data

    async def get_open_orders(self, symbol: str = None):
        endpoint = "/api/v3/openOrders"
        params = {'timestamp': int(time.time() * 1000)}
        if symbol:
            params['symbol'] = symbol
        params['signature'] = self.gen_signature(params)
        async with self.session.get(self.url + endpoint, params=params, headers=self.header) as response:
            data = await response.json()
            if response.status != 200:
                raise Exception(f"Error getting open orders: {data['msg']}")
            return data


