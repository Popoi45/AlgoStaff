import utils.binance as binance 
import utils.bybit as bybit
from utils.keys.BinanceApi import PUBLIC_KEY as API_KEY_BINANCE, SECRET_KEY as SECRET_KEY_BINANCE
from utils.keys.BybitApi import API_PUBLIC as API_PUBLIC_BYBIT, API_PRIVATE as SECRET_KEY_BYBIT 


client_bin_fut =  binance.Futures(API_KEY_BINANCE, SECRET_KEY_BINANCE, testnet=True)
cliient_bybit_fut = bybit.Client(API_PUBLIC_BYBIT,SECRET_KEY_BYBIT, testnet=True)

symbol = 'BTCUSDT'
long = 'BUY'
short = 'SELL'

def order_placer(str: symbol,float: qty):
    client_bin_fut.new_order(symbol = symbol,side='BUY',type='MARKET',quantity=qty,newOrderRespType='RESULT')
    client_bin_fut.new_order(symbol = symbol,side='BUY')



