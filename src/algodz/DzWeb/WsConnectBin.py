import json
import time
import traceback
import websocket
import threading

class Socket_Connection_Binance(websocket.WebSocketApp):
    def __init__(self, url = None, topics = None, futures = True, on_message_handler = None, on_connect = None):
        base_url = "wss://fstream.binance.com" if futures else "wss://stream.binance.com:9443"
        if url: 
            base_url = url
        super().__init__(
            url = f"{base_url}/stream",
            on_open= self.on_open,
            on_message=on_message_handler or self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.handler = on_message_handler
        self.on_connect = on_connect
        self.topics = None
        if isinstance(topics, str):
            self.topics = [topics]
        else:
            self.topics = topics
            
    def on_open(self, ws):
        print(ws, 'Websocket was opened')
        if self.topics:
            self.send_subscribe(self.topics)
        if self.on_connect:
            self.on_connect(ws)
    
    def on_error(self, ws, error):
        print('on_error', ws, error)
        print(traceback.format_exc())
    
    def on_close(self, ws, status, msg):
        print('on_close', ws, status, msg)
    
    def on_message(self, ws, msg):
        data = json.loads(msg)
        print("Def Handler", data)
        
    def send_subscribe(self, topics, unsubcribe = False):
        data = {
            "method": "UNSUBSCRIBE" if unsubcribe else "SUBSCRIBE",
            "params": topics,
            "id": 1234455667
        }
        self.send(json.dumps(data))
            