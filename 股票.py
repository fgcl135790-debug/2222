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
stock_code = st.sidebar.text_input("監控股票代號", value="2409")

# --- 💡 核心演算法：動態計算大戶門檻 ---
def get_dynamic_big_order_threshold(price, total_volume_lots):
    if price >= 500: return 5       
    elif price >= 100: return 20      
    elif price >= 50: return 50      
    else:
        # 低價股(如友達、群創)，依當日實際總量動態調整
        if total_volume_lots >= 100000: return 400 # 總量破10萬張(今天友達近百萬張)，400張才算大單
        elif total_volume_lots >= 50000: return 200 
        elif total_volume_lots >= 10000: return 100 
        else: return 30  

# --- 🟢 初始化全域狀態 ---
if 'open_price' not in st.session_state: st.session_state.open_price = 0.0
if 'last_stock_code' not in st.session_state: st.session_state.last_stock_code = ""
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'last_trade_key' not in st.session_state: st.session_state.last_trade_key = None

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

st.markdown("---")
st.subheader("🔥 30秒內大戶火網追蹤")
history_counter_spot = st.empty()

st.markdown("---")
st.subheader("🔮 智慧多空訊號即時提醒")
signal_spot = st.empty()

# --- 核心邏輯：當沖多空連續性辨識引擎 ---
def process_market_logic(current_price, total_bid_vol, total_ask_vol, big_order_vol):
    open_p = st.session_state.open_price
    now_time = time.time()
    
    tw_now_str = time.strftime('%H:%M:%S', time.gmtime(now_time + 28800))
    
    st.session_state.order_history = [
        x for x in st.session_state.order_history if now_time - x['timestamp'] <= 30
    ]
    
    recent_buy_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Buy')
    recent_sell_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Sell')
    
    with history_counter_spot.container():
        hc1, hc2 = st.columns(2)
        hc1.metric(label="🔴 30秒內大戶連續吃貨 (外盤) 次數", value=f"{recent_buy_cnt} 次", delta="達 3 次觸發做多" if recent_buy_cnt > 0 else None)
        hc2.metric(label="🟢 30秒內大戶連續倒貨 (內盤) 次數", value=f"{recent_sell_cnt} 次", delta="- 達 3 次觸發做空" if recent_sell_cnt > 0 else None, delta_color="inverse")

    if current_price >= open_p and open_p > 0:
        if total_ask_vol > (total_bid_vol * 1.3) and recent_buy_cnt >= 3:
            return f"🎯 【🔥 訊號：強烈做多】\n\n**觸發時間（台）**：{tw_now_str}\n\n**火力全開**：大戶在 30 秒內連續進行了 **{recent_buy_cnt} 次** 破壞性大單吃貨（每筆皆達 {big_order_vol} 張門檻）！"
            
    if current_price < open_p and open_p > 0:
        if total_bid_vol > (total_ask_vol * 1.3) and recent_sell_cnt >= 3:
            return f"🎯 【💥 訊號：強烈做空】\n\n**觸發時間（台）**：{tw_now_str}\n\n**全面崩盤**：大戶在 30 秒內密集連續瘋狂砸出 **{recent_sell_cnt} 次** 內盤出貨大單！"

    return f"⏳ 偵測中：未出現『30秒內連續3筆以上大單 ({big_order_vol}張)』，大戶尚未全面攤牌..."

# --- API 自動連線機制 ---
if api_key:
    client = RestClient(api_key=api_key)
    
    @st.fragment(run_every=1.0)
    def start_streaming(code):
        try:
            quote = client.stock.intraday.quote(symbol=code)
            current_price = quote.get('closePrice') or quote.get('lastPrice') or 0.0
            open_price = quote.get('openPrice') or current_price
            
            # 🟢 【重大修復】從正確的 quote['total']['volume'] 抽取富果即時總成交量(股)，並除以1000換算成張
            total_info = quote.get('total', {})
            raw_volume = total_info.get('volume', 0)
            total_volume_lots = int(raw_volume / 1000) if raw_volume > 0 else 0
            
            if current_price == 0.0:
                price_spot.warning("⏳ 盤後時間或目前無即時成交數據...")
                return
                
            if st.session_state.open_price == 0.0:
                st.session_state.open_price = open_price
                
            # 🎯 由於總量精準抓到了，這裡會正確噴出「400張」的大戶定義！
            dynamic_threshold = get_dynamic_big_order_threshold(current_price, total_volume_lots)
            threshold_spot.write(f"⚙️ **智慧系統動態設定**：目前 `{code}` 大戶定義為單筆成交達 **{dynamic_threshold} 張** 以上。 (今日總量: {total_volume_lots:,} 張)")
            
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
                    c1.text(f"{b_vol:,} 張" if b_vol > 0 else "-")
                    c2.text(f"{b_price}" if b_price > 0 else "-")
                    a_price = asks[i].get('price', 0.0)
                    a_vol = int(asks[i].get('size', 0) / 1000)
                    c3.text(f"{a_price}" if a_price > 0 else "-")
                    c4.text(f"{a_vol:,} 張" if a_vol > 0 else "-")
            
            last_trade = quote.get('lastTrade', {})
            tick_qty = int(last_trade.get('size', 0) / 1000)
            tick_price = last_trade.get('price', current_price)
            last_bid = last_trade.get('bid', 0)
            last_ask = last_trade.get('ask', 0)
            trade_time = last_trade.get('time', 0)
            
            current_trade_key = (trade_time, tick_qty, tick_price)
            
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= dynamic_threshold:
                if tick_price >= last_ask and last_ask > 0:
                    current_side = 'Buy'
                elif tick_price <= last_bid and last_bid > 0:
                    current_side = 'Sell'
                else:
                    current_side = 'Buy' if tick_price >= st.session_state.open_price else 'Sell'
                
                st.session_state.order_history.append({
                    'timestamp': time.time(),
                    'side': current_side
                })
                st.session_state.last_trade_key = current_trade_key
            
            tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
            
            price_spot.metric(
                label=f"📊 股票 {code} 即時價", 
                value=f"{current_price} 元",
                delta=f"相較今日開盤: {round(current_price - st.session_state.open_price, 2)} 元"
            )
            time_spot.metric(label="⏱️ 數據時間", value=tw_time_str)
            
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
