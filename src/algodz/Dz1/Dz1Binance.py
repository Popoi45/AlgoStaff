import requests

def get_request(endpoint,params = None):
    base_url = "https://fapi.binace.com"
    response = requests.get(base_url + endpoint, params = params)
    result = response.json()
    return result

endpoint_tiker = "/fapi/v1/ticker/24hr"
ticker = get_request(endpoint_tiker,'BTCUSDT')
print('Tiker >>',ticker)   
    