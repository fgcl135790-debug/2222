import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 手機畫面基本設定 ---
st.set_page_config(page_title="動態大戶五檔監控", page_icon="⚡", layout="centered")

st.title("⚡ 大戶籌碼偵測 ＋ 即時五檔 APP")
st.write("本程式已成功對接富果 API，全面解鎖秒級『最佳五檔』與『大戶動態籌碼』監控。")

# --- 側邊欄設定 ---
st.sidebar.header("🔑 權限與標的設定")
api_key = st.sidebar.text_input("輸入你的富果 API Key", type="password")
stock_code = st.sidebar.text_input("監控股票代號", value="3481")

# --- 💡 核心演算法：動態計算大戶門檻 ---
def get_dynamic_big_order_threshold(price, total_volume_lots):
    if price >= 500:
        return 5       
    elif price >= 100:
        return 20      
    elif price >= 50:
        return 50      
    else:
        if total_volume_lots >= 100000:
            return 400 
        elif total_volume_lots >= 50000:
            return 200 
        elif total_volume_lots >= 10000:
            return 100 
        else:
            return 30  

# 初始化全域狀態
if 'open_price' not in st.session_state: st.session_state.open_price = 0.0
if 'last_stock_code' not in st.session_state: st.session_state.last_stock_code = ""

if st.session_state.last_stock_code != stock_code:
    st.session_state.open_price = 0.0
    st.session_state.last_stock_code = stock_code

# --- 建立手機即時顯示看板 ---
col_p, col_t = st.columns([2, 1])
price_spot = col_p.empty()
time_spot = col_t.empty()
threshold_spot = st.empty()

st.markdown("---")

# --- 🎯 新增：最佳五檔專屬看板區 ---
st.subheader("📊 盤口最佳五檔 (Best 5)")
five_ticks_spot = st.empty()

st.markdown("---")
st.subheader("🔮 智慧多空訊號即時提醒")
signal_spot = st.empty()

# --- 核心邏輯：當沖多空精準辨識引擎 ---
def process_market_logic(current_price, tick_qty, side, total_bid_vol, total_ask_vol, big_order_vol):
    open_p = st.session_state.open_price
    is_big_order = tick_qty >= big_order_vol
    
    if current_price >= open_p and open_p > 0:
        if total_ask_vol > (total_bid_vol * 1.3) and side == 'Buy' and is_big_order:
            return f"🎯 【🔥 訊號：強烈做多】\n\n**主力動作**：五檔外盤高掛 {total_ask_vol} 張假壓盤，但明細出現主力敲進 {tick_qty} 張外盤大單（大於動態門檻 {big_order_vol} 張）。\n\n**實戰建議**：多方強勢吃貨，順勢現股做多。"
            
    if current_price < open_p and open_p > 0:
        if total_bid_vol > (total_ask_vol * 1.3) and side == 'Sell' and is_big_order:
            return f"🎯 【💥 訊號：強烈做空】\n\n**主力動作**：五檔內盤掛有 {total_bid_vol} 張假撐盤，但明細遭到主力砸出 {tick_qty} 張內盤大單（大於動態門檻 {big_order_vol} 張）。\n\n**實戰建議**：大戶瘋狂出貨，順勢現券放空。"

    return f"⏳ 偵測中：目前單筆成交未達大戶門檻 ({big_order_vol} 張)，大戶尚未亮牌..."

# --- API 自動連線機制 ---
if api_key:
    client = RestClient(api_key=api_key)
    
    @st.fragment(run_every=1.0)
    def start_streaming(code):
        try:
            quote = client.stock.intraday.quote(symbol=code)
            
            current_price = quote.get('closePrice') or quote.get('lastPrice') or 0.0
            open_price = quote.get('openPrice') or current_price
            
            raw_volume = quote.get('volume', 0)
            total_volume_lots = int(raw_volume / 1000) if raw_volume > 0 else 0
            
            if current_price == 0.0:
                price_spot.warning("⏳ 盤後時間或目前無即時成交數據...")
                return
                
            if st.session_state.open_price == 0.0:
                st.session_state.open_price = open_price
                
            dynamic_threshold = get_dynamic_big_order_threshold(current_price, total_volume_lots)
            threshold_spot.write(f"⚙️ **智慧系統動態設定**：目前 `{code}` 大戶定義為單筆成交達 **{dynamic_threshold} 張** 以上。 (今日總量: {total_volume_lots} 張)")
            
            # 1. 抓取並安全防呆處理五檔數據
            bids = quote.get('bids', [])
            asks = quote.get('asks', [])
            while len(bids) < 5: bids.append({'price': 0.0, 'size': 0})
            while len(asks) < 5: asks.append({'price': 0.0, 'size': 0})
            
            total_bid_vol = sum([b.get('size', 0) for b in bids])
            total_ask_vol = sum([a.get('size', 0) for a in asks])
            
            # 2. 繪製精美的五檔對稱排版 (利用 container 局部打包)
            with five_ticks_spot.container():
                # 表頭
                h_col1, h_col2, h_col3, h_col4 = st.columns([1, 1, 1, 1])
                h_col1.markdown("**🟩 買張 (Lots)**")
                h_col2.markdown("**🟩 買價 (Bid)**")
                h_col3.markdown("**🟥 賣價 (Ask)**")
                h_col4.markdown("**🟥 賣張 (Lots)**")
                
                # 逐層輸出五檔 (從 第一檔 顯示到 第五檔)
                for i in range(5):
                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                    
                    # 買盤資訊 (顯示買一到買五)
                    b_price = bids[i].get('price', 0.0)
                    b_vol = int(bids[i].get('size', 0) / 1000)
                    c1.text(f"{b_vol} 張" if b_vol > 0 else "-")
                    c2.text(f"{b_price}" if b_price > 0 else "-")
                    
                    # 賣盤資訊 (顯示賣一到賣五)
                    a_price = asks[i].get('price', 0.0)
                    a_vol = int(asks[i].get('size', 0) / 1000)
                    c3.text(f"{a_price}" if a_price > 0 else "-")
                    c4.text(f"{a_vol} 張" if a_vol > 0 else "-")
            
            # 提取最新一筆交易明細明細
            last_trade = quote.get('lastTrade', {})
            tick_qty = last_trade.get('size', 0)
            tick_price = last_trade.get('price', current_price)
            last_bid = last_trade.get('bid', 0)
            last_ask = last_trade.get('ask', 0)
            
            if tick_price >= last_ask and last_ask > 0:
                side = 'Buy'
            elif tick_price <= last_bid and last_bid > 0:
                side = 'Sell'
            else:
                side = 'Buy' if tick_price >= st.session_state.open_price else 'Sell'
            
            # 更新基本計分板
            price_spot.metric(
                label=f"📊 股票 {code} 即時價", 
                value=f"{current_price} 元",
                delta=f"相較開盤: {round(current_price - st.session_state.open_price, 2)} 元"
            )
            time_spot.metric(label="⏱️ 數據時間", value=time.strftime("%H:%M:%S"))
            
            # 執行多空判定
            decision = process_market_logic(
                current_price, tick_qty, side, total_bid_vol, total_ask_vol, dynamic_threshold
            )
            
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

    start_streaming(stock_code)
else:
    st.warning("🔑 請先在左側邊欄輸入你的「富果 API Key」以啟動功能。")
