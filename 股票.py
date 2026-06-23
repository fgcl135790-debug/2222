import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 手機畫面基本設定 ---
st.set_page_config(page_title="大戶多空即時監控", page_icon="⚡", layout="centered")

st.title("⚡ 大戶籌碼多空自動偵測 APP (真・API連線版)")
st.write("本程式已成功對接富果 API，每秒自動抓取真實五檔與逐筆大單。")

# --- 側邊欄設定（手機點選左上角箭頭展開） ---
st.sidebar.header("🔑 權限與標的設定")
api_key = st.sidebar.text_input("輸入你的富果 API Key", type="password")
stock_code = st.sidebar.text_input("監控股票代號", value="3481")
big_order_volume = st.sidebar.number_input("定義大戶單筆成交門檻 (張)", value=200, step=50)

# --- 🤖 聰明切換機制：換股票時，自動重設基準價 ---
if 'open_price' not in st.session_state: 
    st.session_state.open_price = 0.0
if 'last_stock_code' not in st.session_state:
    st.session_state.last_stock_code = ""

# 如果使用者在左側換了股票代號，把舊股票的開盤價洗掉，重新抓取
if st.session_state.last_stock_code != stock_code:
    st.session_state.open_price = 0.0
    st.session_state.last_stock_code = stock_code

# --- 建立手機即時顯示看板 ---
col_p, col_t = st.columns([2, 1])
price_spot = col_p.empty()
time_spot = col_t.empty()

st.markdown("---")
st.subheader("🔮 智慧多空訊號即時提醒")
signal_spot = st.empty()

# --- 核心邏輯：當沖多空精準辨識引擎 ---
def process_market_logic(current_price, tick_qty, side, total_bid_vol, total_ask_vol):
    open_p = st.session_state.open_price
    is_big_order = tick_qty >= big_order_volume
    
    # ---------------- 🚨 【做多訊號提醒】 ----------------
    if current_price >= open_p and open_p > 0:
        if total_ask_vol > (total_bid_vol * 1.3) and side == 'Buy' and is_big_order:
            return f"🎯 【🔥 訊號：強烈做多】\n\n**主力動作**：五檔外盤高掛 {total_ask_vol} 張假壓盤，但明細出現主力敲進 {tick_qty} 張外盤大單（真吃貨）。\n\n**實戰建議**：多方控盤極強，順勢現股買進做多，停損設跌破今日開盤價 ({open_p} 元)。"
            
    # ---------------- 🚨 【做空訊號提醒】 ----------------
    if current_price < open_p and open_p > 0:
        if total_bid_vol > (total_ask_vol * 1.3) and side == 'Sell' and is_big_order:
            return f"🎯 【💥 訊號：強烈做空】\n\n**主力動作**：五檔內盤掛有 {total_bid_vol} 張假撐盤，但明細遭到主力不計代價砸出 {tick_qty} 張內盤大單（真倒貨）。\n\n**實戰建議**：多頭踩踏開始，順勢現券賣出做空，停損設突破今日開盤價 ({open_p} 元)。"

    return "⏳ 偵測中：目前市場多空平衡，或單筆張數未達大戶門檻，大戶尚未亮牌，請觀望..."

# --- API 自動連線機制 ---
if api_key:
    # 初始化富果官方 RestClient
    client = RestClient(api_key=api_key)
    
    @st.fragment(run_every=1.0)
    def start_streaming(code):
        try:
            # 📡 透過你的 API Key 真正向富果雲端抓取即時快照報價
            quote = client.stock.intraday.quote(symbol=code)
            
            # 擷取真實數據
            current_price = quote.get('closePrice') or quote.get('lastPrice') or 0.0
            open_price = quote.get('openPrice') or current_price
            
            if current_price == 0.0:
                price_spot.warning("⏳ 盤後時間或目前無即時成交數據...")
                return
                
            if st.session_state.open_price == 0.0:
                st.session_state.open_price = open_price
                
            # 自動計算五檔加總
            bids = quote.get('bids', [])
            asks = quote.get('asks', [])
            total_bid_vol = sum([b.get('size', 0) for b in bids])
            total_ask_vol = sum([a.get('size', 0) for a in asks])
            
            # 自動提取最新一筆明細
            last_trade = quote.get('lastTrade', {})
            tick_qty = last_trade.get('size', 0)
            tick_price = last_trade.get('price', current_price)
            last_bid = last_trade.get('bid', 0)
            last_ask = last_trade.get('ask', 0)
            
            # 自動分辨內外盤
            if tick_price >= last_ask and last_ask > 0:
                side = 'Buy'
            elif tick_price <= last_bid and last_bid > 0:
                side = 'Sell'
            else:
                side = 'Buy' if tick_price >= st.session_state.open_price else 'Sell'
            
            # 1. 更新手機面板數字（這次價格跟漲跌會完全即時連動！）
            price_spot.metric(
                label=f"📊 股票 {code} 即時價", 
                value=f"{current_price} 元",
                delta=f"相較今日開盤: {round(current_price - st.session_state.open_price, 2)} 元"
            )
            time_spot.metric(label="⏱️ 數據時間", value=time.strftime("%H:%M:%S"))
            
            # 2. 自動執行多空引擎判別
            decision = process_market_logic(
                current_price, tick_qty, side, total_bid_vol, total_ask_vol
            )
            
            # 3. 根據結果輸出對應的提示
            if "強烈做多" in decision:
                signal_spot.success(decision)
            elif "強烈做空" in decision:
                signal_spot.error(decision)
            else:
                signal_spot.info(decision)
                
        except FugleAPIError as e:
            price_spot.error(f"富果 API 錯誤: {e.message}")
        except Exception as e:
            price_spot.error(f"連線異常: {e}")

    # 啟動自動監控
    start_streaming(stock_code)
else:
    msg = "🔑 請先在左側邊欄輸入你的「富果 API Key」以啟動功能。"
    st.warning(msg)
