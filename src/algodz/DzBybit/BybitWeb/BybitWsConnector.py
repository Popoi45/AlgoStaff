import json
import time
import traceback
import websocket
import traceback

class Socket_Bybit_Connector(websocket.WebSocketApp):
    #wss://stream.bybit.com/v5/public/spot
    #wss://stream.bybit.com/v5/public/linear
    #wss://stream.bybit.com/v5/public/inverse
    #wss://stream.bybit.com/v5/public/spread
    #wss://stream.bybit.com/v5/public/option
    def __init__(
        self,
        url = None, 
        topic = None, 
        futures = True,
        spot = False,
        inverse = False,
        spread = False, 
        option = False,
        on_message_handler = None,
        on_connect = None
        ):
        markets = [futures, spot, inverse, spread, option]
        def return_market(market):
            if futures: 
                market = 'linear'
            if spot:
                market = 'spot'
            if inverse:
                market = 'inverse'
            if spread:
                market = 'spread'
            if option:
                market = 'option'
            return market
        
        base_url = f'wss://stream.bybit.com/v5/public/{return_market(markets)}'
        if url:
            base_url = url
        super().__init__(
            url=f'{base_url}',
            on_open=self.on_open,
            on_message=self.on_message or on_message_handler,
            on_error=self.on_error
        )