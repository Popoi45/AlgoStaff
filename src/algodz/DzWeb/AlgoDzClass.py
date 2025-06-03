from pybit.unified_trading import HTTP 
import requests

def getOrderBookPyBit(category: str ,symbols: list = None,limit: int = 1 ,testnet: bool = True):
    session = HTTP(testnet = testnet)
    tikers = []
    for symbol in symbols:
        response = session.get_orderbook(category=category,symbol=symbol.upper(),limit = limit,testnet = True)
        if response['retCode'] == 0:
            item = response['result']
            tikers.append({
                'symbol':item['s'],
                'ask': item['a'],
                'bid': item['b'],
            })
    return tikers
  