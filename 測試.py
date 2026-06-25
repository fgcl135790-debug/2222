from fugle_marketdata import RestClient

client = RestClient(api_key="你的APIKEY")

try:
    quote = client.stock.intraday.quote(symbol="2330")
    print(quote)
except Exception as e:
    print(type(e))
    print(e)
