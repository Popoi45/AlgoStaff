import json
import threading
import time
import traceback
import websocket


class Socket_conn_Bybit(websocket.WebSocketApp):

    def __init__(self, futures=False, handler=None, topics=None):
        category = "linear" if futures else "spot"
        super().__init__(
            url=f"wss://stream.bybit.com/v5/public/{category}",
            on_open=self.on_open,
            on_message=handler or self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        if isinstance(topics, str):
            self.topics = [topics]
        else:
            self.topics = topics

        # self.run_forever(ping_interval=15, ping_timeout=10)


    def on_open(self, ws):
        print(ws, 'Websocket was opened')
        self.ws = ws
        # Subscription data:
        if self.topics:
            self.send_subscribe(self.topics)


    def on_error(self, ws, error):
        print('on_error', ws, error)
        print(traceback.format_exc())


    def on_close(self, ws, status, msg):
        print('on_close', ws, status, msg)


    def on_message(self, ws, msg):
        # print('on_message', ws, msg)
        data = json.loads(msg)
        print("Default handler", data)

    def send_subscribe(self, topics, unsubscribe=False):
        data = {
            "op": "unsubscribe" if unsubscribe else "subscribe",
            "args": topics
        }
        self.send(json.dumps(data))



