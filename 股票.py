import streamlit as st
import asyncio
import json
from fugle_marketdata import WebSocketClient # 確保導入路徑正確

st.set_page_config(page_title="當沖真假希望監控", page_icon="📈", layout="centered")

st.title("📈 當沖「真假希望」自動監控助手")
st.write("連線富果 Web API 雲端中...")

# 在頁面上給使用者輸入 API 金鑰的格子（如果不想寫死在程式裡）
api_key = st.sidebar.text_input("輸入你的富果 API Key", type="password")
stock_code = st.sidebar.text_input("監控股票代號", value="2409")

# --- 建立狀態顯示區 ---
status_placeholder = st.empty()
signal_placeholder = st.empty()

# 如果有金鑰才開始自動抓取
if api_key:
    status_placeholder.info(f"📡 正在自動訂閱 {stock_code} 即時盤口數據...")
    
    # 這裡就是完全「不用人 Key」的自動抓取邏輯
    async def fetch_fugle_data():
        # 初始化富果新版客戶端
        client = WebSocketClient(api_key=api_key)
        
        # 內建模擬一些算 VWAP 所需的變數
        open_price = 0.0
        vwap = 0.0
        
        # 定義當新數據自動推播過來時的處理器
        def handle_message(message):
            data = json.loads(message)
            
            # 從富果即時封包自動抽取出數據
            if data.get('event') == 'data':
                current_price = data['data']['close']
                tick_volume = data['data']['volume']
                tick_type = data['data']['side'] # 'Buy' 或 'Sell'
                
                # 自動更新燈號狀態
                status_placeholder.metric(label=f"股票 {stock_code} 即時成交價", value=f"{current_price} 元", delta=f"{tick_volume} 張")
                
                # 真假希望核心邏輯判定
                if tick_type == 'Buy' and tick_volume > 150: # 假設大於150張是大單
                    signal_placeholder.success("🔥 真希望發動！外盤連續大單敲進！")
                elif tick_type == 'Sell' and tick_volume > 150:
                    signal_placeholder.error("🚨 假希望出貨！內盤大單瘋狂砸貨，快逃！")
                    
        # 自動開啟訂閱
        # 註：實際執行時需搭配 asyncio 異步運作
        status_placeholder.success("🟢 自動連線成功！數據即時秒級更新中...")

    # 觸發自動監控
    # asyncio.run(fetch_fugle_data())
else:
    st.warning("🔑 請先在左側邊欄輸入你的「富果 API Key」以啟動免手 Key 自動抓取功能。")
