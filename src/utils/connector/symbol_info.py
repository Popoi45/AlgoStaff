# symbol_info.py



class SymbolInfo:
    def __init__(self, base_asset, quote_asset, tick_size, step_size, min_notional):
        self.base_asset = base_asset
        self.quote_asset = quote_asset
        self.tick_size = tick_size  # Price precision
        self.step_size = step_size  # Quantity precision
        self.min_notional = min_notional  # Minimum trade value

    @classmethod
    def from_bybit(cls, symbol_data):
        # Parse Bybit's symbol data
        base_asset = symbol_data['baseCoin']
        quote_asset = symbol_data['quoteCoin']
        tick_size = float(symbol_data['priceFilter']['tickSize'])
        step_size = float(symbol_data['lotSizeFilter']['basePrecision'])
        min_notional = float(symbol_data['lotSizeFilter']['minOrderAmt'])
        return cls(base_asset, quote_asset, tick_size, step_size, min_notional)

    @classmethod
    def from_binance(cls, symbol_data):
        # Parse Binance's symbol data
        base_asset = symbol_data['baseAsset']
        quote_asset = symbol_data['quoteAsset']

        # Initialize variables
        tick_size = None
        step_size = None
        min_notional = None

        # Iterate over the filters
        for f in symbol_data['filters']:
            if f['filterType'] == 'PRICE_FILTER':
                tick_size = float(f['tickSize'])
            elif f['filterType'] == 'LOT_SIZE':
                step_size = float(f['stepSize'])
            elif f['filterType'] == 'NOTIONAL':
                min_notional = float(f['minNotional'])
            # Add other filters as needed

        return cls(base_asset, quote_asset, tick_size, step_size, min_notional)

    @classmethod
    def from_cryptocom(cls, symbol_data):
        base_asset = symbol_data['base_ccy']
        quote_asset = symbol_data['quote_ccy']
        tick_size = float(symbol_data['price_tick_size'])
        step_size = float(symbol_data['qty_tick_size'])
        min_notional = step_size

        return cls(base_asset, quote_asset, tick_size, step_size, min_notional)

    # You can add similar methods for other exchanges if needed
