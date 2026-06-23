import asyncio
import json
# 導入富果即時行情 WebSokcet 套件
from fugle_marketdata import WebMqttClient 

# 這個函式會「自動接收」市場上最新的即時逐筆成交，免人手Key
async def on_new_tick(message):
    data = json.loads(message)
    
    # 程式自動抓取欄位
    current_price = data['close']  # 最新成交價
    tick_volume = data['volume']   # 本筆成交張數
    tick_type = data['side']       # Buy=外盤(紅字), Sell=內盤(綠字)
    
    print(f"📡 [第三方自動抓取] 友達最新成交: {current_price} 元, {tick_volume} 張")
    
    # 這裡直接套入我們寫好的「真假希望」判斷邏輯
    # if current_price > vwap ... (自動執行判定)

async def main():
    # 只要填入網頁申請的免費金鑰 (Key)
    client = WebMqttClient(api_key="YOUR_FREE_API_KEY")
    
    # 程式自動向雲端訂閱友達的即時成交明細與五檔
    await client.subscribe_trades("2409") 
    
    # 綁定自動觸發事件
    client.on_trade = on_new_tick
    await client.connect()

# 讓網頁保持自動監聽
# asyncio.run(main())
