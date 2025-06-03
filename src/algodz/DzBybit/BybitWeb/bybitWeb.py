from pybit.unified_trading import WebSocket
from time import sleep

ws = WebSocket(
    testnet = True,
    channel_type="linear",
)

def handle_message(message):
    print(message)
ws.ticker_stream(
    symbol = 'BTCUSDT',
    callback=handle_message
)
while True:
    sleep(1)