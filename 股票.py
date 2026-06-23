import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 手機畫面基本設定 ---
st.set_page_config(page_title="大戶連續性監控", page_icon="⚡", layout="centered")

st.title("⚡ 大戶籌碼偵測 APP (連續性偵測版)")
st.write("已導入【30秒滾動窗口演算法】，只有當大戶在短時間內連續密集表態，才會觸發多空提醒。")

# --- 側邊欄設定 ---
st.sidebar.header("🔑 權限與標的設定")
api_key = st.sidebar.text_input("輸入你的富果 API Key", type="password")
stock_code = st.sidebar.text_input("監控股票代號", value="3481")

# --- 💡 核心演算法：動態計算大戶門檻 ---
def get_dynamic_big_order_threshold(price, total_volume_lots):
    if price >= 500: return 5       
    elif price >= 100: return 20      
    elif price >= 50: return 50      
    else:
        if total_volume_lots >= 100000: return 400 
        elif total_volume_lots >= 50000: return 200 
        elif total_volume_lots >= 10000: return 100 
        else: return 30  

# --- 🟢 初始化全域狀態（跨秒級重新整理記憶庫） ---
if 'open_price' not in st.session_state: st.session_state.open_price = 0.0
if 'last_stock_code' not in st.session_state: st.session_state.last_stock_code = ""
# 用來存放 30 秒內大單歷史的清單
if 'order_history' not in st.session_state: st.session_state.order_history = []
# 用來防止重複抓到同一筆成交快照的檢查器
if 'last_trade_key' not in st.session_state: st.session_state.last_trade_key = None

# 更換股票時，清空所有狀態與歷史紀錄
if st.session_state.last_stock_code != stock_code:
    st.session_state.open_price = 0.0
    st.session_state.order_history = []
    st.session_state.last_trade_key = None
    st.session_state.last_stock_code = stock_code

# --- 建立手機即時顯示看板 ---
col_p, col_t = st.columns([2, 1])
price_spot = col_p.empty()
time_spot = col_t.empty()
threshold_spot = st.empty()

st.markdown("---")
st.subheader("📊 盤口最佳五檔 (Best 5)")
five_ticks_spot = st.empty()

# 新增：動態展示連續性大單累積狀態的計分板
st.markdown("---")
st.subheader("🔥 30秒內大戶火網追蹤")
history_counter_spot = st.empty()

st.markdown("---")
st.subheader("🔮 智慧多空訊號即時提醒")
signal_spot = st.empty()

# --- 核心邏輯：當沖多空連續性辨識引擎 ---
def process_market_logic(current_price, total_bid_vol, total_ask_vol, big_order_vol):
    open_p = st.session_state.open_price
    
    # 1. 清洗歷史紀錄：只保留 30 秒內的大單，超過的踢掉
    now_time = time.time()
    st.session_state.order_history = [
        x for x in st.session_state.order_history if now_time - x['timestamp'] <= 30
    ]
    
    # 2. 計算 30 秒內，大戶總共敲進幾次外盤、砸出幾次內盤
    recent_buy_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Buy')
    recent_sell_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Sell')
    
    # 3. 在畫面上即時打出目前的火力累積狀況
    with history_counter_spot.container():
        hc1, hc2 = st.columns(2)
        hc1.metric(label="🔴 30秒內大戶連續吃貨 (外盤) 次數", value=f"{recent_buy_cnt} 次", delta="達 3 次觸發做多" if recent_buy_cnt > 0 else None)
        hc2.metric(label="🟢 30秒內大戶連續倒貨 (內盤) 次數", value=f"{recent_sell_cnt} 次", delta="- 達 3 次觸發做空" if recent_sell_cnt > 0 else None, delta_color="inverse")

    # 4. 判斷多空點火（加入連續 3 次的極限精準門檻）
    if current_price >= open_p and open_p > 0:
        if total_ask_vol > (total_bid_vol * 1.3) and recent_buy_cnt >= 3:
            return f"🎯 【🔥 訊號：強烈做多】\n\n**觸發時間**：{time.strftime('%H:%M:%S')}\n\n**火力全開**：五檔外盤高掛假壓盤，且大戶在 30 秒內連續進行了 **{recent_buy_cnt} 次** 破壞性大單吃貨！\n\n**實戰建議**：這是真正的主力集體表態突破，順勢現股買進做多，停損設跌破開盤價。"
            
    if current_price < open_p and open_p > 0:
        if total_bid_vol > (total_ask_vol * 1.3) and recent_sell_cnt >= 3:
            return f"🎯 【💥 訊號：強烈做空】\n\n**觸發時間**：{time.strftime('%H:%M:%S')}\n\n**全面崩盤**：五檔內盤高掛假撐盤，且大戶在 30 秒內密集連續瘋狂砸出 **{recent_sell_cnt} 次** 內盤出貨大單！\n\n**實戰建議**：多頭防線已被打爛，順勢現券賣出放空。"

    return "⏳ 偵測中：盤口雖有波動，但尚未出現『30秒內連續3筆以上大單』的進攻特徵，主力尚未全面攤牌..."

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
            
            # 五檔對稱排版輸出
            bids = quote.get('bids', [])
            asks = quote.get('asks', [])
            while len(bids) < 5: bids.append({'price': 0.0, 'size': 0})
            while len(asks) < 5: asks.append({'price': 0.0, 'size': 0})
            total_bid_vol = sum([b.get('size', 0) for b in bids])
            total_ask_vol = sum([a.get('size', 0) for a in asks])
            
            with five_ticks_spot.container():
                h_col1, h_col2, h_col3, h_col4 = st.columns([1, 1, 1, 1])
                h_col1.markdown("**🟩 買張**")
                h_col2.markdown("**🟩 買價**")
                h_col3.markdown("**🟥 賣價**")
                h_col4.markdown("**🟥 賣張**")
                for i in range(5):
                    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                    b_price = bids[i].get('price', 0.0)
                    b_vol = int(bids[i].get('size', 0) / 1000)
                    c1.text(f"{b_vol} 張" if b_vol > 0 else "-")
                    c2.text(f"{b_price}" if b_price > 0 else "-")
                    a_price = asks[i].get('price', 0.0)
                    a_vol = int(asks[i].get('size', 0) / 1000)
                    c3.text(f"{a_price}" if a_price > 0 else "-")
                    c4.text(f"{a_vol} 張" if a_vol > 0 else "-")
            
            # --- 🚀 連續性大單即時判定與記錄機制 ---
            last_trade = quote.get('lastTrade', {})
            tick_qty = int(last_trade.get('size', 0) / 1000) # 轉成張數
            tick_price = last_trade.get('price', current_price)
            last_bid = last_trade.get('bid', 0)
            last_ask = last_trade.get('ask', 0)
            trade_time = last_trade.get('time', 0)
            
            # 建立這筆交易的唯一識別碼，防止重複抓取計數
            current_trade_key = (trade_time, tick_qty, tick_price)
            
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= dynamic_threshold:
                # 判斷這筆真實大單是內盤還是外盤
                if tick_price >= last_ask and last_ask > 0:
                    current_side = 'Buy'
                elif tick_price <= last_bid and last_bid > 0:
                    current_side = 'Sell'
                else:
                    current_side = 'Buy' if tick_price >= st.session_state.open_price else 'Sell'
                
                # 寫入記憶庫
                st.session_state.order_history.append({
                    'timestamp': time.time(),
                    'side': current_side
                })
                # 更新識別碼
                st.session_state.last_trade_key = current_trade_key
            
            # 更新股價計分板
            price_spot.metric(
                label=f"📊 股票 {code} 即時價", 
                value=f"{current_price} 元",
                delta=f"相較今日開盤: {round(current_price - st.session_state.open_price, 2)} 元"
            )
            time_spot.metric(label="⏱️ 數據時間", value=time.strftime("%H:%M:%S"))
            
            # 2. 執行帶有連續性過濾的多空判別
            decision = process_market_logic(current_price, total_bid_vol, total_ask_vol, dynamic_threshold)
            
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
