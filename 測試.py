from fugle_marketdata import RestClient

client = RestClient(api_key="你的KEY")

quote = client.stock.intraday.quote(symbol="2409")

print(quote)
