import math
import time

from utils.api import ws_bybit
from utils.keys.BinanceApi import PUBLIC_KEY as API_KEY, SECRET_KEY as SECRET_KEY
from utils.api.binance import Binance_API

symbol = 'AXSUSDT'
order_id = None

def round_up(num, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(num * multiplier)/multiplier

def round_down(num, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(num * multiplier) / multiplier


def get_symbol_details(client: Binance_API, our_symbol = None):
    result = {}
    raw_result = client.get_exchange_info()

    print(raw_result)
    
    for symbol in raw_result['symbols']:
        look_symbol = symbol['symbol']
        if our_symbol and look_symbol != our_symbol:
            continue
        
        price_digit = lot_digit = min_notional = None
        for filter in symbol['filters']:
            if filter['filterType'] == 'PRICE_FILTER':
                price_digit = int(filter['tickSize'].index('1') - 1)
            elif filter['filterType'] == 'LOT_SIZE':
                lot_digit = int(filter['stepSize'].index('1')-1) if float(filter['stepSize']) < 1 else 0
            elif filter['filterType'] == 'MIN_NOTIONAL' or (
                not client.futures and filter['filterType'] == 'NOTIONAL'):
                min_notional_key = 'notional' if filter['filterType'] == 'MIN_NOTIONAL' else 'minNotional'
                min_notional = float(filter[min_notional_key])
                
        result[look_symbol] = {
            'min_notional': min_notional,
            'price_digit': price_digit,
            'lot_digit': lot_digit
        }
    return result.get(our_symbol, result)

client = Binance_API(api_key=API_KEY, secret_key=SECRET_KEY, futures=True)       

symbol_info = get_symbol_details(client=client, our_symbol=symbol)

print(symbol_info)


qty1 = 3.11
qty2 =3.11

qty1 = round(qty1, symbol_info['lot_digit'])
qty2 = round(qty2, symbol_info['lot_digit'])

priceBuy = symbol_info['price_digit']*0.9
priceSell = symbol_info['price_digit']*1.1

priceBuy = round(priceBuy, symbol_info['price_digit'])
priceSell = round(priceSell, symbol_info['price_digit'])

print(qty1,qty2)
print(priceBuy,priceSell)

long_order = client.post_limit_order(symbol=symbol,side='BUY',quantity= qty1, price=priceBuy)
short_order = client.post_limit_order(symbol=symbol,side='SELL',quantity=qty2,price=priceSell)

if "orderId" in long_order:
    long_order_id = long_order['orderId']
    print(long_order_id)
else: 
    print(long_order)

if 'orderId' in short_order:
    short_order_id = short_order['orderId']
    print(short_order_id)
else:
    print(short_order)

time.sleep(5)

if long_order_id and short_order_id:
    cancel_all_orders = client.delete_cancel_all_open_orders(symbol=symbol)
   print(cancel_all_orders)


