import hashlib
import hmac
import json
import time
import urllib.parse
from .base_api import BaseApi
import aiohttp
from .symbol_info import SymbolInfo
from config import CRYPTOCOM_API_KEY, CRYPTOCOM_SECRET_KEY, TEST_API_KEY, TEST_SECRET_KEY, TEST_MODE

if TEST_MODE:
    api_key = TEST_API_KEY
    secret_key = TEST_SECRET_KEY
else:
    api_key = CRYPTOCOM_API_KEY
    secret_key = CRYPTOCOM_SECRET_KEY

class CryptocomApiAsync(BaseApi):
    def __init__(self):
        self.api_key = api_key
        self.secret_key = secret_key
        self.url = "https://api.crypto.com/exchange/v1/"
        self.header = {}
        self.symbol_info = {}
        self.session = None
        self.num_request = 0

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

    def gen_signature(self, payload_str):
        sign = hmac.new(bytes(self.secret_key, "utf-8"), payload_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return sign


    async def request(self, endpoint, params, ws_call=False):
        param_str = ""
        MAX_LEVEL = 3
        def params_to_str(obj, level):
            if level >= MAX_LEVEL:
                return str(obj)
            return_str = ""
            for key in sorted(obj):
                return_str += key
                if obj[key] is None:
                    return_str += 'null'
                elif isinstance(obj[key], list):
                    for subObj in obj[key]:
                        return_str += params_to_str(subObj, level + 1)
                else:
                    return_str += str(obj[key])
            return return_str
        timestamp = int(time.time() * 1000)
        req = {
            "id": str(timestamp+self.num_request),
            "nonce": timestamp,
            "method": endpoint,
            "api_key": self.api_key,
            "params": params
        }
        self.num_request += 1
        if "params" in req:
            param_str = params_to_str(req['params'], 0)
        payload_str = req['method'] + req['id'] + req['api_key'] + param_str + str(req['nonce'])
        req['sig'] = self.gen_signature(payload_str)
        if ws_call:
            return req
        try:
            async with self.session.post(self.url + endpoint, json=req) as response:
                text = await response.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = None
                if response.status != 200 or data is None:
                    print("Error Response Status:", response.status)
                    print("Error Response Headers:", response.headers)
                    print("Error Response Text:", text)
                    raise Exception(f"Error response: {text}")
        except Exception as e:
            print("ERROR:", e)
            raise
        if self.num_request > 99:
            self.num_request = 0
        return data

    async def get_symbols_info(self):
        self.symbol_info = {}
        endpoint = 'public/get-instruments'
        async with self.session.get(self.url + endpoint) as response:
            data = await response.json()
            if data:
                symbols_data = data['result']['data']
                for symbol_data in symbols_data:
                    symbol_info = SymbolInfo.from_cryptocom(symbol_data)
                    self.symbol_info[symbol_data['symbol']] = symbol_info

    async def get_exchange_info(self, symbol: str = None):
        data = None
        endpoint = 'public/get-instruments'
        params = {}
        try:
            async with self.session.get(self.url + endpoint, params=params) as response:
                raw_data = await response.json()
        except Exception:
            raise Exception(f"Error on execution: {raw_data.text}")
        if raw_data:
            if symbol:
                for el in raw_data['result']['data']:
                    if el['symbol'] == symbol:
                        data = el
            else:
                data = raw_data['result']['data']
        return data


    async def get_order_book(self, symbol: str):
        endpoint = 'public/get-book'
        params = {'instrument_name': symbol, 'depth': 1}
        try:
            async with self.session.get(self.url + endpoint, params=params) as response:
                raw_data = await response.json()
        except Exception:
            raise Exception(f"Error on execution: {raw_data.text}")
        data = raw_data['result']['data'][0]
        ask_price = float(data['asks'][0][0])
        bid_price = float(data['bids'][0][0])
        return ask_price, bid_price



    async def post_limit_order(self, symbol, side, quantity, price, reduce_only=False, rounding="down"):
        endpoint = "private/create-order"
        params = {
            'instrument_name': symbol,
            'side': side.upper(),
            'type': 'LIMIT',
            'quantity': str(self.round_from_size(quantity, self.symbol_info[symbol].step_size)),
            'price': str(self.round_from_size(price, self.symbol_info[symbol].tick_size, rounding=rounding)),
            'timeInForce': 'GOOD_TILL_CANCEL',
        }
        print(f"Debug params: {params}")
        return await self.request(endpoint, params)



    async def post_cancel_order(self, symbol: str=None, orderId = None, origClientOrderId: str = None):
        endpoint = "private/cancel-order"
        params = {}
        if orderId or origClientOrderId:
            if orderId:
                params['order_id'] = orderId
            if origClientOrderId:
                params['client_oid'] = origClientOrderId
        return await self.request(endpoint, params)

    async def post_cancel_all_open_orders(self, symbol: str = None):
        endpoint = "private/cancel-all-orders"
        params = {}
        if symbol:
            params['instrument_name'] = symbol
        return await self.request(endpoint, params)

    async def get_coins_balance(self, coin: str = None):
        endpoint = "private/user-balance"
        params = {}
        result = await self.request(endpoint, params)
        if result and coin:
            result = result['result']['data'][0]['position_balances']
            for position in result:
                if position['instrument_name'] == coin:
                    result = float(position['max_withdrawal_balance'])
        return result

    async def get_open_orders(self, symbol: str=None):
        endpoint = "private/get-open-orders"
        params = {}
        if symbol:
            params['instrument_name'] = symbol
        response = await self.request(endpoint, params)
        result = response['result']['data']
        return result



