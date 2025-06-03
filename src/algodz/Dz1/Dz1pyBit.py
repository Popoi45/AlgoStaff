from pybit.unified_trading import HTTP
import os
from dotenv import load_dotenv

load_dotenv("../env/api.env")

BYBIT_API = os.getenv('API_KEY') 
BYBIT_API_SECRET = os.getenv('API_SECRET')
TESTNET = False

session = HTTP(
    api_key = BYBIT_API,
    api_secret = BYBIT_API_SECRET,
    testnet = TESTNET,
)
sumbols=['ETHUSDT','BTCUSDT','SOLUSDT','ADAUSDT','1INCHUSDT','BANDUSDT','1000PEPEUSDT','TRUMPUSDT','IOTAUSDT']

def load10symbols(symbols,category):
    tikers = []
    for symbol in symbols:
        response = session.get_tickers(category=category,symbol=symbol)
        if response['retCode'] == 0:
            item = response['result']['list'][0]
            tikers.append({
                'symbol':item['symbol'],
                'highPrice24h': item['highPrice24h'],
                'lowPrice24h': item['lowPrice24h'],
            })
    return tikers        

print(load10symbols(category='linear',symbols=sumbols))

