import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="centered")

st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 📱 手機版大優化：把隱藏的側邊欄改為主畫面折疊收納盒 ---
with st.expander("⚙️ 點我展開：輸入金鑰 / 更換股票 / 模擬測試", expanded=False):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    test_mode = st.checkbox("🌙 啟動深夜模擬測試 (半夜看畫面專用)", value=False)

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

# --- 📱 手機版版面配置：最重要資訊放最上面 ---
# 1. 價格與時間區塊
price_container = st.container()
# 2. 多空訊號燈（一秒看風向）
signal_spot = st.empty()
# 3. 動態門檻文字
threshold_spot = st.empty()
st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

# 4. 最佳五檔區
st.write("📋 **盤口最佳五檔**")
five_ticks_spot = st.empty()
st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

# 5. 火網追蹤區
st.write("🔥 **30秒大戶進攻火網**")
history_counter_spot = st.empty()

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
    
    # 📱 手機優化：利用不變形 HTML 表格並排顯示累積次數，防爆版
    counter_html = f"""
    <table style='width:100%; text-align:center; font-size:14px;'>
        <tr>
            <td style='width:50%; background-color:#1e261e; padding:6px; border-radius:4px;'>
                <span style='color:#ff4466;font-size:12px;'>🔴 30s外盤大單吃貨</span><br>
                <b style='color:#ff4466;font-size:20px;'>{recent_buy_cnt} 次</b>
            </td>
            <td style='width:4px;'></td>
            <td style='width:50%; background-color:#19222a; padding:6px; border-radius:4px;'>
                <span style='color:#00ff88;font-size:12px;'>🟢 30s內盤大單倒貨</span><br>
                <b style='color:#00ff88;font-size:20px;'>{recent_sell_cnt} 次</b>
            </td>
        </tr>
    </table>
    """
    history_counter_spot.markdown(counter_html, unsafe_allow_html=True)

    if current_price >= open_p and open_p > 0:
        if total_ask_vol > (total_bid_vol * 1.3) and recent_buy_cnt >= 3:
            return f"🎯【🔥 做多訊號】大戶30秒內爆買 {recent_buy_cnt} 次！主力突破吃貨，順勢現股做多！"
            
    if current_price < open_p and open_p > 0:
        if total_bid_vol > (total_ask_vol * 1.3) and recent_sell_cnt >= 3:
            return f"🎯【💥 做空訊號】大戶30秒內爆賣 {recent_sell_cnt} 次！多頭防線潰散，順勢放空！"

    return f"⏳ 偵測中：未出現30秒內連續3筆以上大單 ({big_order_vol}張)，保持觀望..."

# --- API 連線與測試模式控制機制 ---
if api_key or test_mode:
    client = RestClient(api_key=api_key) if api_key else None
    
    @st.fragment(run_every=1.0)
    def start_streaming(code):
        try:
            if test_mode:
                current_price, open_price, total_volume_lots = 29.05, 31.10, 954591
                bids = [{'price': 29.05, 'size': 3472000}, {'price': 29.00, 'size': 14373000}, {'price': 28.95, 'size': 1419000}, {'price': 28.90, 'size': 2476000}, {'price': 28.85, 'size': 1445000}]
                asks = [{'price': 29.10, 'size': 652000}, {'price': 29.15, 'size': 180000}, {'price': 29.20, 'size': 131000}, {'price': 29.25, 'size': 745000}, {'price': 29.30, 'size': 437000}]
                tick_qty, tick_price, last_bid, last_ask, trade_time = 450, 29.00, 29.05, 29.10, time.time()
            else:
                quote = client.stock.intraday.quote(symbol=code)
                current_price = quote.get('closePrice') or quote.get('lastPrice') or 0.0
                open_price = quote.get('openPrice') or current_price
                total_info = quote.get('total', {})
                raw_volume = total_info.get('volume', 0)
                
                if raw_volume == 0:
                    try:
                        ticker_info = client.stock.intraday.ticker(symbol=code)
                        raw_volume = ticker_info.get('volume', 0)
                    except: pass
                total_volume_lots = int(raw_volume / 1000) if raw_volume > 0 else 0
                bids, asks = quote.get('bids', []), quote.get('asks', [])
                while len(bids) < 5: bids.append({'price': 0.0, 'size': 0})
                while len(asks) < 5: asks.append({'price': 0.0, 'size': 0})
                
                last_trade = quote.get('lastTrade', {})
                tick_qty = int(last_trade.get('size', 0) / 1000)
                tick_price = last_trade.get('price', current_price)
                last_bid = last_trade.get('bid', 0)
                last_ask = last_trade.get('ask', 0)
                trade_time = last_trade.get('time', 0)

            if current_price == 0.0 and not test_mode:
                st.warning("⏳ 目前無即時成交數據...")
                return
                
            if st.session_state.open_price == 0.0:
                st.session_state.open_price = open_price
                
            dynamic_threshold = get_dynamic_big_order_threshold(current_price, total_volume_lots)
            mode_prefix = " (🌙測試中)" if test_mode else ""
            threshold_spot.caption(f"⚙️ 大戶定義：單筆 {dynamic_threshold} 張以上 | 今日總量: {total_volume_lots:,} 張{mode_prefix}")
            
            total_bid_vol = sum([b.get('size', 0) for b in bids])
            total_ask_vol = sum([a.get('size', 0) for a in asks])
            
            # 📱 【手機抗變形黑科技】採用 HTML Table 緊湊排版，強制寬度防上下錯位
            five_ticks_html = """
            <table style='width:100%; text-align:center; font-size:15px; border-collapse:collapse; font-family:monospace;'>
                <tr style='background-color:#111; height:28px;'>
                    <th style='color:#00ff88; width:25%; font-size:12px;'>買張</th>
                    <th style='color:#00ff88; width:25%; font-size:12px;'>買價</th>
                    <th style='color:#ff4466; width:25%; font-size:12px;'>賣價</th>
                    <th style='color:#ff4466; width:25%; font-size:12px;'>賣張</th>
                </tr>
            """
            for i in range(5):
                b_price = bids[i].get('price', 0.0)
                b_vol = int(bids[i].get('size', 0) / 1000)
                a_price = asks[i].get('price', 0.0)
                a_vol = int(asks[i].get('size', 0) / 1000)
                
                b_v_str = f"{b_vol:,}" if b_vol > 0 else "-"
                b_p_str = f"{b_price}" if b_price > 0 else "-"
                a_p_str = f"{a_price}" if a_price > 0 else "-"
                a_v_str = f"{a_vol:,}" if a_vol > 0 else "-"
                
                five_ticks_html += f"""
                <tr style='height:32px; border-bottom:1px solid #222;'>
                    <td style='color:#00ff88; font-size:14px;'>{b_v_str}</td>
                    <td style='color:#00ff88; font-weight:bold;'>{b_p_str}</td>
                    <td style='color:#ff4466; font-weight:bold;'>{a_p_str}</td>
                    <td style='color:#ff4466; font-size:14px;'>{a_v_str}</td>
                </tr>
                """
            five_ticks_html += "</table>"
            five_ticks_spot.markdown(five_ticks_html, unsafe_allow_html=True)
            
            # 大單判定
            current_trade_key = (trade_time, tick_qty, tick_price)
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= dynamic_threshold:
                if tick_price >= last_ask and last_ask > 0: current_side = 'Buy'
                elif tick_price <= last_bid and last_bid > 0: current_side = 'Sell'
                else: current_side = 'Buy' if tick_price >= st.session_state.open_price else 'Sell'
                st.session_state.order_history.append({'timestamp': time.time(), 'side': current_side})
                st.session_state.last_trade_key = current_trade_key
            
            # 更新頂部手機計分板
            tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
            with price_container:
                cp1, cp2 = st.columns([5, 4])
                cp1.header(f"📈 {code} : {current_price} 元")
                cp2.subheader(f"⏱️ {tw_time_str}")
            
            decision = process_market_logic(current_price, total_bid_vol, total_ask_vol, dynamic_threshold)
            if "做多" in decision: signal_spot.success(decision)
            elif "做空" in decision: signal_spot.error(decision)
            else: signal_spot.info(decision)
                
        except FugleAPIError as e: st.error(f"富果 API 錯誤: {e.message}")
        except Exception as e: st.error(f"連線異常: {e}")

    start_streaming(stock_code)
else:
    st.warning("🔑 請先展開上方選單輸入「富果 API Key」以啟動功能。")
