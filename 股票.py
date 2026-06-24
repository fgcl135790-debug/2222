import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 📱 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .block-container {padding-top: 0.5rem; padding-bottom: 0.5rem; max-width: 100% !important;}
    h1 {font-size: 22px !important; margin-bottom: 5px !important;}
    div[data-testid="stExpander"] {margin-bottom: 0.5rem;}
    hr {margin: 6px 0 !important;}
    p, span, label {font-size: 13px !important;}
    </style>
""", unsafe_allow_html=True)

st.title("⚡ 行動大戶籌碼五檔 APP")

with st.expander("⚙️ 設定：輸入金鑰 / 更換股票 / 模擬測試", expanded=False):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        manual_big_order_lots = st.number_input(
            "🔥 大戶定義 (張)", min_value=1, max_value=5000, value=150, step=10
        )
    with col_u2:
        manual_ratio = st.number_input(
            "📊 參考量比 (倍)", min_value=1.0, max_value=5.0, value=1.2, step=0.1, format="%.1f"
        )
        
    test_mode = st.checkbox("🌙 啟動深夜模擬測試 (半夜看畫面專用)", value=False)

retracement_alert_spot = st.empty() 
price_block = st.empty()  
threshold_spot = st.empty()
signal_spot = st.empty()
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:14px; color:#ddd;'>📋 盤口最佳五檔</b>", unsafe_allow_html=True)
five_ticks_spot = st.empty()
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:14px; color:#ddd;'>🔥 30秒大戶進攻火網</b>", unsafe_allow_html=True)
history_counter_spot = st.empty()

st.markdown("<b style='font-size:14px; color:#ddd;'>📜 大戶進攻即時紀錄 (30秒內明細)</b>", unsafe_allow_html=True)
log_spot = st.empty()
# --- 🟢 初始化全域狀態機制 ---
if 'open_price' not in st.session_state: st.session_state.open_price = 0.0
if 'wave_high_price' not in st.session_state: st.session_state.wave_high_price = 0.0
if 'wave_low_price' not in st.session_state: st.session_state.wave_low_price = 999999.0
if 'wave_alert_text' not in st.session_state: st.session_state.wave_alert_text = None       
if 'wave_alert_expires' not in st.session_state: st.session_state.wave_alert_expires = 0.0  
if 'last_stock_code' not in st.session_state: st.session_state.last_stock_code = ""
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'last_trade_key' not in st.session_state: st.session_state.last_trade_key = None
if 'last_update_time' not in st.session_state: st.session_state.last_update_time = time.time()

if st.session_state.last_stock_code != stock_code:
    st.session_state.open_price = 0.0
    st.session_state.wave_high_price = 0.0
    st.session_state.wave_low_price = 999999.0
    st.session_state.wave_alert_text = None
    st.session_state.wave_alert_expires = 0.0
    st.session_state.order_history = []
    st.session_state.last_trade_key = None
    st.session_state.last_stock_code = stock_code

# --- 核心邏輯：當沖多空連續性辨識引擎 ---
def process_market_logic(current_price, total_bid_vol, total_ask_vol, big_order_vol, target_ratio, stock_name):
    open_p = st.session_state.open_price
    now_time = time.time()
    
    st.session_state.order_history = [
        x for x in st.session_state.order_history if now_time - x['timestamp'] <= 30
    ]
    recent_buy_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Buy')
    recent_sell_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Sell')

    if recent_buy_cnt > 0:
        if current_price > st.session_state.wave_high_price:
            st.session_state.wave_high_price = current_price
    else:
        st.session_state.wave_high_price = 0.0

    if recent_sell_cnt > 0:
        if current_price < st.session_state.wave_low_price and current_price > 0:
            st.session_state.wave_low_price = current_price
    else:
        st.session_state.wave_low_price = 999999.0

    RETRACEMENT = 0.01  
    ALERT_DURATION = 5.0  

    # 多頭轉折判定：自高點回撤 1%
    if st.session_state.wave_high_price > 0:
        drop_ratio = (st.session_state.wave_high_price - current_price) / st.session_state.wave_high_price
        if drop_ratio >= RETRACEMENT:
            st.session_state.order_history = []
            st.session_state.wave_high_price = 0.0
            recent_buy_cnt = 0
            st.session_state.wave_alert_text = f"⚠️ 攻勢中斷：股價自這波攻擊高點 {st.session_state.wave_high_price} 元回撤達 {drop_ratio*100:.2f}%！多頭趨勢破壞，強制清空籌碼火網。"
            st.session_state.wave_alert_expires = now_time + ALERT_DURATION

    # 空頭轉折判定：自低點反彈 1%
    if st.session_state.wave_low_price < 999999.0:
        rebound_ratio = (current_price - st.session_state.wave_low_price) / st.session_state.wave_low_price
        if rebound_ratio >= RETRACEMENT:
            st.session_state.order_history = []
            st.session_state.wave_low_price = 999999.0
            recent_sell_cnt = 0
            st.session_state.wave_alert_text = f"💥 空頭止跌：股價自這波低點 {st.session_state.wave_low_price} 元強彈達 {rebound_ratio*100:.2f}%！空方針對性遭到攻破，強制擦除砸貨紀錄。"
            st.session_state.wave_alert_expires = now_time + ALERT_DURATION

    if now_time > st.session_state.wave_alert_expires:
        st.session_state.wave_alert_text = None  

    counter_html = f"<table style='width:100%; text-align:center; font-size:13px;'><tr><td style='width:49%; background-color:#221215; padding:5px; border-radius:4px;'><span style='color:#ff4466;font-size:11px;'>🔴 30s外盤大單吃貨</span><br><b style='color:#ff4466;font-size:18px;'>{recent_buy_cnt} 次</b></td><td style='width:2%;'></td><td style='width:49%; background-color:#112215; padding:5px; border-radius:4px;'><span style='color:#00ff88;font-size:11px;'>🟢 30s內盤大單倒貨</span><br><b style='color:#00ff88;font-size:18px;'>{recent_sell_cnt} 次</b></td></tr></table>"
    history_counter_spot.markdown(counter_html, unsafe_allow_html=True)

    if st.session_state.order_history:
        log_html = "<div style='background-color:#111; padding:6px; border-radius:4px; font-family:monospace; font-size:12px; max-height:100px; overflow-y:auto; text-align:left; border: 1px solid #222;'>"
        for order in reversed(st.session_state.order_history):
            color = "#ff4466" if order['side'] == 'Buy' else "#00ff88"
            action = "外盤搶吃" if order['side'] == 'Buy' else "內盤砸貨"
            log_html += f"<p style='margin:2px 0; color:{color}; line-height:1.2;'>⏱️ {order['time_str']} | {action} <b style='font-size:12px;'>{order['qty']}</b> 張 @ {order['price']} 元</p>"
        log_html += "</div>"
        log_spot.markdown(log_html, unsafe_allow_html=True)
    else:
        log_spot.caption("⏳ 30秒內無大戶表態紀錄...")

    decision_text = f"⏳ 偵測中：未出現30秒內連續3筆精確大戶單 ({big_order_vol}張)，保持觀望..."
    if open_p > 0:
        if current_price >= open_p and recent_buy_cnt >= 3:
            decision_text = f"🎯【🔥 做多訊號】{stock_name} 主力突破吃貨，順勢做多！"
        if current_price < open_p and recent_sell_cnt >= 3:
            decision_text = f"🎯【💥 做空訊號】{stock_name} 多頭防線潰散，順勢放空！"

    return decision_text, st.session_state.wave_alert_text
# --- API 連線與測試模式控制機制 ---
if api_key or test_mode:
    client = RestClient(api_key=api_key) if api_key else None
    
    # 🟢 速度配置：每 1.5 秒高速無感重新整理看盤模式
    @st.fragment(run_every=1.5)
    def start_streaming(code):
        try:
            current_now = time.time()
            elapsed_speed = current_now - st.session_state.last_update_time
            if elapsed_speed > 10.0 or elapsed_speed <= 0: elapsed_speed = 1.50
            st.session_state.last_update_time = current_now

            # =========================================================================
            # 📌 模擬劇本模式
            # =========================================================================
            if test_mode:
                open_price = 29.00
                stock_name = "友達" if code == "2409" else f"股票 {code}"
                total_volume_lots = 95459
                trade_time = int(current_now * 1000)
                
                cycle = int(current_now) % 40
                
                if cycle < 10:
                    # 【階段 1：0~9秒】大戶外盤連續吃貨 ➔ 必定觸發【做多訊號】
                    raw_price = 29.05 + (cycle * 0.04) 
                    current_price = round(raw_price, 2)  
                    tick_qty = manual_big_order_lots + 10 
                    tick_price = current_price
                    bids_base, asks_base = 1000, int(1000 * manual_ratio * 1.5)
                    last_bid, last_ask = round(current_price - 0.05, 2), current_price
                    
                elif cycle < 20:
                    # 【階段 2：10~19秒】高點折返下挫 ➔ 觸發【多頭波段高點下修 1% 獨立警報】
                    raw_price = 29.41 - ((cycle - 10) * 0.05)  
                    current_price = round(raw_price, 2)  
                    tick_qty = 0
                    tick_price = current_price
                    bids_base, asks_base = 2000, 2000
                    last_bid, last_ask = current_price, round(current_price + 0.05, 2)
                    
                elif cycle < 30:
                    # 【階段 3：20~29秒】內盤大量砸貨 ➔ 必定觸發【做空訊號】
                    raw_price = 28.90 - ((cycle - 20) * 0.05)
                    current_price = round(raw_price, 2)  
                    tick_qty = manual_big_order_lots + 20 
                    tick_price = current_price
                    bids_base, asks_base = int(1000 * manual_ratio * 1.5), 1000
                    last_bid, last_ask = current_price, round(current_price + 0.05, 2)
                    
                else:
                    # 【階段 4：30~39秒】止跌回升反彈 ➔ 觸發【空頭波段低點強彈 1% 獨立警報】
                    raw_price = 28.40 + ((cycle - 30) * 0.05)  
                    current_price = round(raw_price, 2)  
                    tick_qty = 0
                    tick_price = current_price
                    bids_base, asks_base = 2000, 2000
                    last_bid, last_ask = round(current_price - 0.05, 2), current_price

                bids = [{'price': round(current_price - 0.05 * i, 2), 'size': bids_base - i * 100} for i in range(1, 6)]
                asks = [{'price': round(current_price + 0.05 * i, 2), 'size': asks_base + i * 100} for i in range(1, 6)]
            # =========================================================================
            # 📌 盤中實時富果資料串接模式（已完全移除大盤與櫃買指數請求）
            # =========================================================================
            else:
                quote = client.stock.intraday.quote(symbol=code)
                current_price = quote.get('lastTrade', {}).get('price') or quote.get('closePrice') or 0.0
                open_price = quote.get('priceOpen') or quote.get('openPrice') or current_price
                stock_name = quote.get('name') or f"股票 {code}"
                
                total_info = quote.get('total', {})
                raw_volume = total_info.get('unit') or total_info.get('volume', 0)
                if raw_volume == 0:
                    try:
                        ticker_info = client.stock.intraday.ticker(symbol=code)
                        raw_volume = ticker_info.get('volume', 0)
                        if stock_name == f"股票 {code}":
                            stock_name = ticker_info.get('name') or f"股票 {code}"
                    except: pass
                
                total_volume_lots = int(raw_volume) if raw_volume > 0 else 0
                
                raw_bids = quote.get('bids', [])
                raw_asks = quote.get('asks', [])
                bids = raw_bids if isinstance(raw_bids, list) else []
                asks = raw_asks if isinstance(raw_asks, list) else []
                while len(bids) < 5: bids.append({'price': 0.0, 'size': 0})
                while len(asks) < 5: asks.append({'price': 0.0, 'size': 0})
                
                last_trade_raw = quote.get('lastTrade')
                if isinstance(last_trade_raw, list) and len(last_trade_raw) > 0:
                    last_trade = last_trade_raw
                elif isinstance(last_trade_raw, dict):
                    last_trade = last_trade_raw
                else:
                    last_trade = {}

                tick_qty = int(last_trade.get('unit') or last_trade.get('size', 0))
                tick_price = last_trade.get('price', current_price)
                trade_time = last_trade.get('time', 0)
                
                last_bid = bids.get('price', 0.0) if bids and isinstance(bids, dict) else 0.0
                last_ask = asks.get('price', 0.0) if asks and isinstance(asks, dict) else 0.0

            # =========================================================================
            # 📌 畫面渲染、即時量比雙色計算防線
            # =========================================================================
            if current_price == 0.0 and not test_mode:
                st.warning("⏳ 目前無即時成交數據...")
                return
            if st.session_state.open_price == 0.0:
                st.session_state.open_price = open_price
                
            total_bid_vol = sum([b.get('size', 0) for b in bids if isinstance(b, dict)])
            total_ask_vol = sum([a.get('size', 0) for a in asks if isinstance(a, dict)])
            
            # 計算精確的五檔委託量比，並透過顏色與文字指引多空策略（不影響大戶燈號）
            if total_bid_vol > 0 and total_ask_vol > 0:
                if total_ask_vol >= total_bid_vol:
                    current_real_ratio = total_ask_vol / total_bid_vol
                    ratio_html = f"量比: <b style='color:#ff4466; font-size:13px;'>{current_real_ratio:.2f} 倍</b> (<span style='color:#ff4466;'>🔴 賣盤壓境：適合突破做多</span>)"
                else:
                    current_real_ratio = total_bid_vol / total_ask_vol
                    ratio_html = f"量比: <b style='color:#00ff88; font-size:13px;'>{current_real_ratio:.2f} 倍</b> (<span style='color:#00ff88;'>🟢 買盤托底：適合主力誘多做空</span>)"
            else:
                ratio_html = "量比: 0.00 倍 (⏳ 計算中)"

            mode_prefix = " (🌙測試中)" if test_mode else ""
            threshold_spot.markdown(
                f"<div style='font-size:12px; color:#aaa;'>⚙️ 門檻: {manual_big_order_lots} 張 | 今日總量: {total_volume_lots:,} 張 | {ratio_html} | ⚡ {elapsed_speed:.2f} 秒/次{mode_prefix}</div>", 
                unsafe_allow_html=True
            )
            
            five_ticks_html = "<table style='width:100%; text-align:center; font-size:13px; border-collapse:collapse; font-family:monospace;'><tr style='background-color:#111; height:22px;'><th style='color:#00ff88; width:25%; font-size:11px;'>買張</th><th style='color:#00ff88; width:25%; font-size:11px;'>買價</th><th style='color:#ff4466; width:25%; font-size:11px;'>賣價</th><th style='color:#ff4466; width:25%; font-size:11px;'>賣張</th></tr>"
            for i in range(5):
                b_price = bids[i].get('price', 0.0) if i < len(bids) and isinstance(bids[i], dict) else 0.0
                b_vol = int(bids[i].get('size', 0)) if i < len(bids) and isinstance(bids[i], dict) else 0
                a_price = asks[i].get('price', 0.0) if i < len(asks) and isinstance(asks[i], dict) else 0.0
                a_vol = int(asks[i].get('size', 0)) if i < len(asks) and isinstance(asks[i], dict) else 0
                b_v_str = f"{b_vol:,}" if b_vol > 0 else "-"
                b_p_str = f"{b_price:.2f}" if b_price > 0 else "-"
                a_p_str = f"{a_price:.2f}" if a_price > 0 else "-"
                a_v_str = f"{a_vol:,}" if a_vol > 0 else "-"
                five_ticks_html += f"<tr style='height:24px; border-bottom:1px solid #1c1c1c;'><td style='color:#00ff88;'>{b_v_str}</td><td style='color:#00ff88; font-weight:bold;'>{b_p_str}</td><td style='color:#ff4466; font-weight:bold;'>{a_p_str}</td><td style='color:#ff4466;'>{a_v_str}</td></tr>"
            five_ticks_html += "</table>"
            five_ticks_spot.markdown(five_ticks_html, unsafe_allow_html=True)
            
            current_trade_key = (trade_time, tick_qty, tick_price)
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= manual_big_order_lots:
                if tick_price >= last_ask and last_ask > 0: current_side = 'Buy'
                elif tick_price <= last_bid and last_bid > 0: current_side = 'Sell'
                else: current_side = 'Buy' if tick_price >= st.session_state.open_price else 'Sell'
                
                tw_tick_time = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
                st.session_state.order_history.append({
                    'timestamp': time.time(), 'time_str': tw_tick_time,
                    'side': current_side, 'qty': tick_qty, 'price': tick_price
                })
                st.session_state.last_trade_key = current_trade_key
            
            p_diff = current_price - st.session_state.open_price
            p_color = "#ff4466" if p_diff >= 0 else "#00ff88"
            tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
            price_block.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom: 2px;'>"
                f"<span style='font-size:16px; font-weight:bold;'>📈 {stock_name} ({code})</span>"
                f"<span style='font-size:18px; font-weight:bold; color:{p_color};'>{current_price:.2f} <span style='font-size:12px;'>({p_diff:+.2f})</span> <span style='color:#888; font-size:11px; font-weight:normal;'>{tw_time_str}</span></span>"
                f"</div>", unsafe_allow_html=True
            )
            
            decision, alert = process_market_logic(current_price, total_bid_vol, total_ask_vol, manual_big_order_lots, manual_ratio, stock_name)
            
            if alert:
                retracement_alert_spot.warning(alert)
            else:
                retracement_alert_spot.empty()
                
            # =========================================================================
            # 🎯 台股自訂紅漲綠跌 HTML 高對比訊號燈塊
            # =========================================================================
            if "做多" in decision:
                signal_spot.markdown(
                    f"<div style='background-color:#2e1518; padding:8px; border-radius:4px; border-left:5px solid #ff4466; color:#ff4466; font-size:14px; font-weight:bold;'>{decision}</div>", 
                    unsafe_allow_html=True
                )
            elif "做空" in decision:
                signal_spot.markdown(
                    f"<div style='background-color:#122618; padding:8px; border-radius:4px; border-left:5px solid #00ff88; color:#00ff88; font-size:14px; font-weight:bold;'>{decision}</div>", 
                    unsafe_allow_html=True
                )
            else:
                signal_spot.markdown(
                    f"<div style='background-color:#161b22; padding:8px; border-radius:4px; border-left:5px solid #58a6ff; color:#c9d1d9; font-size:13px;'>{decision}</div>", 
                    unsafe_allow_html=True
                )
                
        except FugleAPIError as e:
            if "Rate limit exceeded" in str(e) or "429" in str(e):
                st.error("🚨 偵測到富果超頻鎖定！啟動安全防守，強制進入後台冷卻 12 秒解鎖...")
                time.sleep(12)
            else: st.error(f"富果 API 異常: {e}")
        except Exception as e: st.error(f"連線異常: {e}")

    start_streaming(stock_code)
else:
    st.warning("🔑 請先展開上方選單輸入「富果 API Key」或勾選「模擬測試」以啟動功能。")
