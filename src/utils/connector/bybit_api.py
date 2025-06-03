# connector/bybit_api.py - async version
import hashlib
import hmac
import json
import time
import aiohttp
from .base_api import BaseApi
from .symbol_info import SymbolInfo
from config import BYBIT_API_KEY, BYBIT_SECRET_KEY, TEST_API_KEY, TEST_SECRET_KEY, TEST_MODE

if TEST_MODE:
    api_key = TEST_API_KEY
    secret_key = TEST_SECRET_KEY
else:
    api_key = BYBIT_API_KEY
    secret_key = BYBIT_SECRET_KEY

class BybitApiAsync(BaseApi):

    def __init__(self):
        if TEST_MODE:
            print("TEST MODE ENABLED")
        else:
            print("REAL MODE ENABLED")
        self.api_key = api_key
        self.secret_key = secret_key
        self.url = "https://api-demo.bybit.com" if TEST_MODE else "https://api.bybit.com"
        self.header = {
            'X-BAPI-API-KEY': self.api_key,
            "X-BAPI-RECV-WINDOW": "5000",
        }
        self.symbol_info = {}
        self.session = None

    async def initialize(self):
        print("Initializing BybitApiAsync...")
        self.session = aiohttp.ClientSession()
        await self.get_symbols_info()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None


    async def get_symbols_info(self):
        self.symbol_info = {}
        endpoint = '/v5/market/instruments-info'
        params = {'category': 'spot'}
        async with self.session.get(self.url + endpoint, params=params) as response:
            data = await response.json()
            if data:
                symbols_data = data['result']['list']
                for symbol_data in symbols_data:
                    symbol_info = SymbolInfo.from_bybit(symbol_data)
                    self.symbol_info[symbol_data['symbol']] = symbol_info


    def gen_signature(self, mod_params, timestamp):
        param_str = timestamp + self.api_key + '5000' + mod_params
        sign = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return sign

    # async def params_post_json(self, params, endpoint):
    #     post_json = json.dumps(params)
    #     timestamp = str(int(time.time() * 1000))
    #     headers = self.header
    #     headers['X-BAPI-SIGN'] = self.gen_signature(post_json, timestamp)
    #     headers['X-BAPI-TIMESTAMP'] = timestamp
    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(self.url + endpoint, data=json.dumps(params), headers=headers) as response:
    #             data = await response.json()
    #             if data['retCode'] != 0:
    #                 raise Exception(f"Error on execution: {data['retMsg']}")
    #             return data

    async def params_post_json(self, params, endpoint):
        post_json = json.dumps(params)
        timestamp = str(int(time.time() * 1000))
        headers = self.header
        headers['X-BAPI-SIGN'] = self.gen_signature(post_json, timestamp)
        headers['X-BAPI-TIMESTAMP'] = timestamp
        async with self.session.post(self.url + endpoint, data=json.dumps(params), headers=headers) as response:
            data = await response.json()
            if data['retCode'] != 0:
                raise Exception(f"Error on execution: {data['retMsg']}")
            return data

    # async def params_get_str(self, params, endpoint):
    #     params_get_string = '&'.join([f'{k}={v}' for k, v in params.items()])
    #     timestamp = str(int(time.time() * 1000))
    #     headers = self.header
    #     headers['X-BAPI-SIGN'] = self.gen_signature(params_get_string, timestamp)
    #     headers['X-BAPI-TIMESTAMP'] = timestamp
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(self.url + endpoint, params=params, headers=headers) as response:
    #             data = await response.json()
    #             if data['retCode'] != 0:
    #                 raise Exception(f"Error on execution: {data['retMsg']}")
    #             return data

    async def params_get_str(self, params, endpoint):
        params_get_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        timestamp = str(int(time.time() * 1000))
        headers = self.header
        headers['X-BAPI-SIGN'] = self.gen_signature(params_get_string, timestamp)
        headers['X-BAPI-TIMESTAMP'] = timestamp
        async with self.session.get(self.url + endpoint, params=params, headers=headers) as response:
            data = await response.json()
            if data['retCode'] != 0:
                raise Exception(f"Error on execution: {data['retMsg']}")
            return data

    async def get_exchange_info(self, symbol: str = None):
        endpoint = '/v5/market/instruments-info'
        params = {'category': 'spot'}
        if symbol:
            params['symbol'] = symbol
        async with self.session.get(self.url + endpoint, params=params) as response:
            data = await response.json()
            if data['retCode'] != 0:
                raise Exception(f"Error on execution: {data['retMsg']}")
            return data


    async def get_order_book(self, symbol: str, limit: int = 1):
        endpoint = '/v5/market/orderbook'
        params = {'category': 'spot', 'symbol': symbol, 'limit': limit}
        async with self.session.get(self.url + endpoint, params=params) as response:
            data = await response.json()
            ask_price = float(data['result']['a'][0][0])
            bid_price = float(data['result']['b'][0][0])
            return ask_price, bid_price


    async def post_limit_order(self, symbol, side, quantity, price, reduce_only=False, rounding="down", post_only=False):
        endpoint = "/v5/order/create"
        params = {
            'category': 'spot',
            'symbol': symbol,
            'side': side.capitalize(),
            'orderType': 'Limit',
            'qty': str(self.round_from_size(quantity, self.symbol_info[symbol].step_size)),
            'price': str(self.round_from_size(price, self.symbol_info[symbol].tick_size, rounding=rounding)),
        }
        if post_only:
            params['timeInForce'] = 'PostOnly'
        print("Debug qty:", params['qty'], params)
        if reduce_only:
            params['reduceOnly'] = reduce_only

        result = await self.params_post_json(params, endpoint)
        response = result['result']
        return response

    async def post_cancel_order(self, symbol: str, orderId = None, orderLinkId: str = None):
        if orderId:
            orderId = str(orderId)
        endpoint = "/v5/order/cancel"
        params = {
            'category': 'spot',
            'symbol': symbol,
        }
        if orderId:
            params['orderId'] = orderId
        elif orderLinkId:
            params['orderLinkId'] = orderLinkId
        else:
            return print("No paramether orderId")

        result = await self.params_post_json(params, endpoint)
        return result

    async def post_cancel_all_open_orders(self, symbol: str = None):
        endpoint = "/v5/order/cancel-all"
        params = {
            'category': 'spot'
        }
        if symbol:
            params['symbol'] = symbol
        result = await self.params_post_json(params, endpoint)
        return result


    async def get_coins_balance(self, coin: str = None):
        if TEST_MODE:
            return 1000000
        endpoint = "/v5/asset/transfer/query-account-coins-balance"
        params = {
            'accountType': 'UNIFIED'
        }
        if coin:
            params['coin'] = coin
        result = await self.params_get_str(params, endpoint)
        if result and coin:
            result = result['result']['balance']
            for el in result:
                if el['coin'] == coin:
                    result = float(el['transferBalance'])
        return result

    async def get_open_orders(self, symbol: str=None):
        endpoint = "/v5/order/realtime"
        params = {
            'category': 'spot'
        }
        if symbol:
            params['symbol'] = symbol
        response = await self.params_get_str(params, endpoint)
        result = response['result']['list']
        return result
