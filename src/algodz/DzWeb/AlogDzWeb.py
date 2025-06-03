from AlgoDzClass import getOrderBookPyBit
from pybit.unified_trading import HTTP
from WsConnectBin import Socket_Connection_Binance
import time
import json
import threading

symbols = ['BTCUSDT','ETHUSDT','ADAUSDT','1INCHUSDT','bandusdt','1000PEPEUSDT','XRPUSDT','SUIUSDT','SOLUSDT','TRUMPUSDT']
typeF = "linear"
typeS = "spot"
typeFlimit  = 1





#From kkline: s, E, in k: i, o, c, h, l, v, n, x, V, Q
def handler(ws, msg):
    data = json.loads(msg)
    print(data)


topic = 'solusdt@kline_1m'



ws_Binance = (Socket_Connection_Binance(topics = topic,on_message_handler=handler))
thread = threading.Thread(target=ws_Binance.run_forever)
thread.start()
#data = getOrderBookPyBit(category=typeF,symbols=symbols,limit = typeFlimit,testnet=True)

#for item in data:
#    print(item)
   
    

