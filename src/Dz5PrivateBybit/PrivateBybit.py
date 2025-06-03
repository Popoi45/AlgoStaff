import math 
import json
from threading import Thread
import threading
import time
from decimal import Decimal


from utils.api.bybit import Bybit_api
from utils.keys.BybitApi import API_PUBLIC as API_KEY,API_PRIVATE as API_SECRET
from utils.api.ws_bybit import Socket_conn_Bybit

symbol = 'ADAUSDT'
symbol_price = None
price_recived = False


order_id_long = None
order_id_long1 = None
order_id_short = None


def round_up(num, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(num * multiplier)/multiplier

def round_down(num, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(num * multiplier) / multiplier


def get_symbol_details(client: Bybit_api,our_symbol = None):
    result = {}
    raw_result = client.get_instruments_info()
    #print('Raw Api Response: ', raw_result)

    for item in raw_result['list']:
        look_symbol = item['symbol']
        if our_symbol and look_symbol != our_symbol:
            continue
        
        price_digit = lot_digit = min_notional = None
        price_digit = int(item['priceFilter']['tickSize'].index('1') - 1)
        lot_digit = int(item['lotSizeFilter']['qtyStep'].index('1') - 1) if float(item['lotSizeFilter']['qtyStep']) < 1 else 0 
        min_notional = int(item['lotSizeFilter']['minNotionalValue']) 

        result[look_symbol] = {
                'min_notional':min_notional,
                'price_digit': price_digit,
                'lot_digit': lot_digit
                }
    return result.get(look_symbol,result)
        


client = Bybit_api(api_key=API_KEY, secret_key=API_SECRET,futures= True)

symbol_info=get_symbol_details(client=client,our_symbol=symbol)

print(symbol_info)

def handler(ws, msg):
    global symbol_price,symbol,price_recived
    response = json.loads(msg)
    if 'data' in response and 'lastPrice' in response['data']:
        symbol_price = float(response['data']['lastPrice'])
        price_recived = True
        ws.close()

ws_test = Socket_conn_Bybit(topics=f'tickers.{symbol}', handler=handler)

thread = threading.Thread(target=ws_test.run_forever)
thread.start()

while not price_recived:
    time.sleep(0.5)

if price_recived:
    print('Цена Получена: ',symbol_price)

thread.join()

qty = 10
long = 'BUY'
short = 'SELL'
order_ids = []

def price_for_order(price, percentage, symbol):
    price_digit = symbol_info[symbol]['price_digit']
    if percentage is None:
        raise ValueError("Percentage must not be None")
    return round(price * percentage, price_digit)
 


if symbol_info[symbol]['lot_digit'] == 0:
    qty = int(qty)
else:
    qty = round(qty,symbol_info[symbol]['lot_digit'])

order_long_1 = client.post_limit_order(symbol=symbol,side=long,qty=qty,price=price_for_order(symbol_price,0.99,symbol))
order_long_2 = client.post_limit_order(symbol=symbol,side=long,qty=qty,price=price_for_order(symbol_price,0.98,symbol))
order_short = client.post_limit_order(symbol=symbol,side=short,qty=qty,price=price_for_order(symbol_price,1.2,symbol))

if 'orderId' in order_long_1:
    order_id_long = order_long_1['orderId']
    order_ids.append(order_id_long)
else:
    print(order_long_1)

if 'orderId' in order_long_2:
    order_id_long1 = order_long_2['orderId']
    order_ids.append(order_id_long1)
else:
    print(order_long_2)

if 'orderId' in order_short:
    order_id_short = order_short['orderId']
    order_ids.append(order_id_short)
else:
    print(order_short)

time.sleep(5)

for id in order_ids:
    close_order = client.post_cancel_order(symbol,id)
    print('Order Closed:', id)


