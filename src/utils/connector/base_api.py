import math
from decimal import Decimal, getcontext, ROUND_DOWN, ROUND_UP, ROUND_HALF_UP

class BaseApi:
    def round_from_size(self, number, size, rounding='down'):
        getcontext().prec = 28
        str_size = str(size)
        decimal_size = -Decimal(str_size.rstrip('0')).as_tuple().exponent
        number_decimal = Decimal(str(number))
        size_decimal = Decimal(str(size))

        if rounding == 'down':
            # first_round = math.floor(number / size) * size
            first_round = (number_decimal / size_decimal).to_integral_value(rounding=ROUND_DOWN) * size_decimal
        elif rounding == 'up':
            # first_round = math.ceil(number / size) * size
            first_round = (number_decimal / size_decimal).to_integral_value(rounding=ROUND_UP) * size_decimal
        else:  # 'nearest'
            # first_round = round(number / size) * size
            first_round = (number_decimal / size_decimal).to_integral_value(rounding=ROUND_HALF_UP) * size_decimal

        # last_round = round(first_round, decimal_size)
        last_round = first_round.quantize(Decimal('1.' + '0' * decimal_size))

        return last_round

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass  # Or raise NotImplementedError if necessary

    async def initialize(self):
        raise NotImplementedError

    async def get_exchange_info(self):
        raise NotImplementedError

    async def get_order_book(self, symbol: str):
        raise NotImplementedError

    async def get_coins_balance(self, coin: str):
        raise NotImplementedError

    async def get_open_orders(self, symbol: str=None):
        raise NotImplementedError

    async def post_limit_order(self, symbol, side, quantity, price, rounding='down'):
        raise NotImplementedError

    async def post_cancel_order(self, symbol, order_id):
        raise NotImplementedError

    async def post_cancel_all_open_orders(self, symbol):
        raise NotImplementedError


