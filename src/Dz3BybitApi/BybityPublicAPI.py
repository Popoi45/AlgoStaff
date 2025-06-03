import requests
import websocket
import json
from utils.api.ws_bybit import Socket_conn_Bybit
import threading

#API Base Url Builder
host = 'api-testnet.bybit.com'
version = 'v5'
product = 'market'

#API task Url
module ='orderbook'
category = 'linear'
symbols = ['BTCUSDT','ETHUSDT','SOLUSDT','1000PEPEUSDT','XRPUSDT','HYPEUSDT','SUIUSDT','BANDUSDT','AAVEUSDT','ADAUSDT']
symbol = 'ADAUSDT'
limit = 1
endpoints = [f'{module}?category={category}&symbol={symbol.upper()}&limit={limit}' for symbol in symbols]


base_url = f'https://{host}/{version}/{product}/'

def make_request(base_url, endpoints):
    results = []
    for endpoint in endpoints:
        url = base_url + endpoint
        response = requests.get(url)
        result = response.json()
        results.append(result)
    return results

results = make_request(base_url=base_url, endpoints=endpoints)
for symbol, result in zip(symbols,results):
    print(f'---{symbol}---')
    if 'result' in result:
        r = result['result']
        best_bid = [{'price': float(bid[0]), "qty": float(bid[1])} for bid in r.get('b',[])]
        best_ask = [{'price': float(ask[0]), "qty": float(ask[1])} for ask in r.get('a',[])]
        
        best_bid_ask = {
            'Best Bid': best_bid,
            'Best Ask': best_ask
        }
        
        print(json.dumps(best_bid_ask,indent=4))
        
#topics = ['orderbook.1.AXSUSDT','kline.1.AXSUSDT','orderbook.1.SOLUSDT','kline.1.SOLUSDT']
topics = [f'tickers.{symbol}']
ws_bybit = Socket_conn_Bybit(topics=topics)
thread = threading.Thread(target=ws_bybit.run_forever, args=(None, None,15,10))
thread.start() 
