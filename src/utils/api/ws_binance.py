import json
import traceback
# pip install websocket-client
import websocket
import threading

class Socket_conn_Binance(websocket.WebSocketApp):
    def __init__(self, topics=None, futures=False, on_message_handler=None, on_connect=None):
        base_url = "wss://fstream.binance.com" if futures else "wss://stream.binance.com:9443"
        super().__init__(
            url=f"{base_url}/stream",
            on_open=self.on_open,
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
        # self.run_forever()

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
        print("Default handler", data)


    def send_subscribe(self, topics, unsubscribe=False):
        data = {
            "method": "UNSUBSCRIBE" if unsubscribe else "SUBSCRIBE",
            "params": topics,
            "id": 1110021
        }
        self.send(json.dumps(data))
