import hashlib
import hmac
import json
import time
import requests


class Bybit_api:
    BASE_LINK = "https://api-testnet.bybit.com"
    def __init__(self, api_key='test', secret_key='test', futures=False, **kwargs):
        self.api_key = api_key
        self.secret_key = secret_key
        self.futures = futures
        if self.futures:
            self.category = "linear"
        else:
            self.category = "spot"
        self.header = {
            'X-BAPI-API-KEY': self.api_key,
            "X-BAPI-RECV-WINDOW": "5000",
        }

    def gen_signature(self, mod_params, timestamp):
        param_str = timestamp + self.api_key + '5000' + mod_params
        sign = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"), hashlib.sha256).hexdigest()
        return sign

    def http_request(self, method, endpoint, params):
        """
        Отправляет http запрос на сервер торговой площадки

        :param endpoint: url адрес запроса
        :param method: тип запроса (GET, POST)
        :param params: тело запроса (params)

        :return: :class:Response (requests.models.Response)
        """
        timestamp = str(int(time.time() * 1000))
        if method == 'GET':
            params_get_string = '&'.join([f'{k}={v}' for k, v in params.items()])
            sign = self.gen_signature(params_get_string, timestamp)
            self.header['X-BAPI-SIGN'] = sign
            self.header['X-BAPI-TIMESTAMP'] = timestamp
            response = requests.get(url=self.BASE_LINK + endpoint, params=params, headers=self.header)
        elif method == "POST":
            params_post_json = json.dumps(params)
            sign = self.gen_signature(params_post_json, timestamp)
            self.header['X-BAPI-SIGN'] = sign
            self.header['X-BAPI-TIMESTAMP'] = timestamp
            print(f"Debug print: params: {params}, headers: {self.header} =============")
            response = requests.post(url=self.BASE_LINK + endpoint, data=json.dumps(params), headers=self.header)
        else:
            print("Метод не известен!")
            return None

        if response:  # Проверяем если ответ не пустой - чтоб не получить ошибки форматирования пустого ответа.
            response = response.json()
            if response['retCode'] != 0:
                raise Exception(response['retMsg'])
        else:
            raise Exception(response.text)

        return response['result']

    def get_klines(self, symbol: str, interval: str, start: int = None, end: int = None, limit=200):
        endpoint = "/v5/market/kline"
        method = "GET"
        params = {
            'category': self.category,
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        if start:
            params['start'] = start
        if end:
            params['end'] = end
    
        return self.http_request(method=method, endpoint=endpoint, params=params)

    def get_instruments_info(self, symbol: str = None, status: str = None, baseCoin: str = None):
        endpoint = "/v5/market/instruments-info"
        method = "GET"
        params = {
            'category': self.category,
        }
        if symbol:
            params['symbol'] = symbol
        if status:
            params['status'] = status
        if baseCoin:
            params['baseCoin'] = baseCoin


        return self.http_request(method=method, endpoint=endpoint, params=params)

    def post_limit_order(self, symbol: str, side: str, qty, price, reduce_only=False, orderLinkId=None):
        endpoint = "/v5/order/create"
        method = "POST"
        params = {
            'category': self.category,
            'symbol': symbol,
            'side': side.capitalize(), # "BUY" - "Buy"
            'orderType': 'Limit',
            'qty': str(qty),
            'price': str(price)
        }
        if reduce_only:
            params['reduceOnly'] = reduce_only
        if orderLinkId:
            params['orderLinkId'] = orderLinkId

        return self.http_request(method=method, endpoint=endpoint, params=params)

    def post_cancel_order(self, symbol: str, orderId: str = None, orderLinkId: str = None):
        endpoint = "/v5/order/cancel"
        method = "POST"
        params = {
            'category': self.category,
            'symbol': symbol,
        }
        if orderId:
            params['orderId'] = orderId
        if orderLinkId:
            params['orderLinkId'] = orderLinkId

        return self.http_request(method=method, endpoint=endpoint, params=params)

    def post_amend_order(self, symbol: str, orderId: str = None, orderLinkId: str = None, price: str = None, qty: str = None):
        endpoint = "/v5/order/amend"
        method = "POST"
        params = {
            'category': self.category,
            'symbol': symbol,
        }
        if orderId:
            params['orderId'] = orderId
        if orderLinkId:
            params['orderLinkId'] = orderLinkId
        if price:
            params['price'] = str(price)
        if qty:
            params['qty'] = str(qty)

        return self.http_request(method=method, endpoint=endpoint, params=params)

    def get_orders_info(self, symbol: str = None, baseCoin: str = None, settleCoin: str = None, orderId: str = None,
                        orderLinkId: str = None, openOnly: int = 0):
        endpoint = "/v5/position/list"
        method = "GET"
        params = {
            'category': self.category,
        }
        if symbol:
            params['symbol'] = symbol
        elif baseCoin:
            params['baseCoin'] = baseCoin
        elif settleCoin:
            params['settleCoin'] = settleCoin
        if orderId:
            params['orderId'] = orderId
        if orderLinkId:
            params['orderLinkId'] = orderLinkId
        if openOnly:
            params['openOnly'] = openOnly

        return self.http_request(method=method, endpoint=endpoint, params=params)

    def get_position_info(self, symbol: str = None, settleCoin: str = None):
        endpoint = "/v5/position/list"
        method = "GET"
        params = {
            'category': self.category,
        }
        if symbol:
            params['symbol'] = symbol
        elif settleCoin:
            params['settleCoin'] = settleCoin

        if not symbol and not settleCoin:
            raise Exception("symbol or settleCoin need to be specified!")

        return self.http_request(method=method, endpoint=endpoint, params=params)

