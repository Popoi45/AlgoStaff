import requests

def make_request(endpoint, params = None):
    base_url = "http://api.bybit.com"
    response = requests.get(base_url + endpoint, params=params)
    result = response.json()
    return result

if __name__ == '__main__':
    endpoint_tiker = "/v5/market/tickers"
    params = {
        'category': 'linear',
        'symbol':'BTCUSDT'
    }    
    ticker = make_request(endpoint_tiker, params)
    print('Tiker >>',ticker)
