import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 📱 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="centered")

# 使用 CSS 壓縮手機端元件間距，並固定深色底色提高戶外辨識度
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

# --- 📱 把設定選單收納進主畫面的折疊收納盒 ---
with st.expander("⚙️ 設定：輸入金鑰 / 更換股票 / 模擬測試", expanded=False):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    test_mode = st.checkbox("🌙 啟動深夜模擬測試 (半夜看畫面專用)", value=False)

# --- 📱 定義手機單頁即時擦除動態容器鎖定 ---
index_block = st.empty()  
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
if 'wave_high_price' not in st.session_state: st.session_state.wave_high_price = 0.0    # 多頭進攻高點鎖
if 'wave_low_price' not in st.session_state: st.session_state.wave_low_price = 999999.0  # 空頭拋售低點鎖
if 'last_stock_code' not in st.session_state: st.session_state.last_stock_code = ""
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'last_trade_key' not in st.session_state: st.session_state.last_trade_key = None
if 'last_update_time' not in st.session_state: st.session_state.last_update_time = time.time()

if 'taiex_cache' not in st.session_state: st.session_state.taiex_cache = (0.0, 0.0)
if 'otc_cache' not in st.session_state: st.session_state.otc_cache = (0.0, 0.0)
if 'last_index_fetch_time' not in st.session_state: st.session_state.last_index_fetch_time = 0.0

if st.session_state.last_stock_code != stock_code:
    st.session_state.open_price = 0.0
    st.session_state.wave_high_price = 0.0
    st.session_state.wave_low_price = 999999.0
    st.session_state.order_history = []
    st.session_state.last_trade_key = None
    st.session_state.last_stock_code = stock_code

# --- 💡 核心演算法：精細化大戶規則多維矩陣 ---
def get_dynamic_big_order_threshold(price, total_volume_lots):
    if price >= 1000: return 2       
    elif price >= 500: return 5 if total_volume_lots >= 10000 else 3
    elif price >= 200:
        if total_volume_lots >= 500000: return 50
        elif total_volume_lots >= 100000: return 40
        elif total_volume_lots >= 50000: return 30
        elif total_volume_lots >= 10000: return 15
        else: return 5
    elif price >= 100:
        if total_volume_lots >= 500000: return 100
        elif total_volume_lots >= 100000: return 80
        elif total_volume_lots >= 50000: return 50
        elif total_volume_lots >= 10000: return 30
        else: return 10
    elif price >= 50:
        if total_volume_lots >= 500000: return 200
        elif total_volume_lots >= 100000: return 150
        elif total_volume_lots >= 50000: return 100
        elif total_volume_lots >= 10000: return 50
        else: return 20
    elif price >= 20: 
        if total_volume_lots >= 500000: return 500 
        elif total_volume_lots >= 100000: return 300
        elif total_volume_lots >= 50000: return 150
        elif total_volume_lots >= 10000: return 80
        else: return 25
    else: 
        if total_volume_lots >= 500000: return 600
        elif total_volume_lots >= 100000: return 400
        elif total_volume_lots >= 50000: return 200
        elif total_volume_lots >= 10000: return 100
        else: return 30
# --- 核心邏輯：當沖多空連續性辨識引擎（完整雙向波段折返 1% 清空版） ---
def process_market_logic(current_price, total_bid_vol, total_ask_vol, big_order_vol, stock_name):
    open_p = st.session_state.open_price
    now_time = time.time()
    
    # 快速清洗超過 30 秒的老舊紀錄
    st.session_state.order_history = [
        x for x in st.session_state.order_history if now_time - x['timestamp'] <= 30
    ]
    recent_buy_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Buy')
    recent_sell_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Sell')

    # ⚡ 1. 多頭追蹤：連續上升進攻波最高點
    if recent_buy_cnt > 0:
        if current_price > st.session_state.wave_high_price:
            st.session_state.wave_high_price = current_price
    else:
        st.session_state.wave_high_price = 0.0

    # ⚡ 2. 空頭追蹤：連續下跌拋售波最低點
    if recent_sell_cnt > 0:
        if current_price < st.session_state.wave_low_price and current_price > 0:
            st.session_state.wave_low_price = current_price
    else:
        st.session_state.wave_low_price = 999999.0

    # ⚡ 3. 多頭轉折判定：自高點回撤 1% ➔ 清空多頭
    RETRACEMENT = 0.01  
    if st.session_state.wave_high_price > 0:
        drop_ratio = (st.session_state.wave_high_price - current_price) / st.session_state.wave_high_price
        if drop_ratio >= RETRACEMENT:
            st.session_state.order_history = []
            st.session_state.wave_high_price = 0.0
            return f"⚠️ 攻勢中斷：股價自這波攻擊高點 {st.session_state.wave_high_price} 元回撤達 {drop_ratio*100:.2f}%！多頭趨勢破壞，強制清空籌碼，轉為觀望。"

    # ⚡ 4. 空頭轉折判定：自低點反彈 1% ➔ 清空空頭 (止跌回升測試)
    if st.session_state.wave_low_price < 999999.0:
        rebound_ratio = (current_price - st.session_state.wave_low_price) / st.session_state.wave_low_price
        if rebound_ratio >= RETRACEMENT:
            st.session_state.order_history = []
            st.session_state.wave_low_price = 999999.0
            return f"💥 空頭止跌：股價自這波低點 {st.session_state.wave_low_price} 元強彈達 {rebound_ratio*100:.2f}%！空方針對性遭到攻破，強制擦除砸貨明細，全力防守。"

    # 渲染計分板
    counter_html = f"<table style='width:100%; text-align:center; font-size:13px;'><tr><td style='width:49%; background-color:#221215; padding:5px; border-radius:4px;'><span style='color:#ff4466;font-size:11px;'>🔴 30s外盤大單吃貨</span><br><b style='color:#ff4466;font-size:18px;'>{recent_buy_cnt} 次</b></td><td style='width:2%;'></td><td style='width:49%; background-color:#112215; padding:5px; border-radius:4px;'><span style='color:#00ff88;font-size:11px;'>🟢 30s內盤大單倒貨</span><br><b style='color:#00ff88;font-size:18px;'>{recent_sell_cnt} 次</b></td></tr></table>"
    history_counter_spot.markdown(counter_html, unsafe_allow_html=True)

    # 渲染大戶進攻流水帳黑盒子
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

    # 多空核心訊號動態判定
    if open_p > 0:
        if current_price >= open_p and total_ask_vol > (total_bid_vol * 1.2) and recent_buy_cnt >= 3:
            return f"🎯【🔥 做多訊號】{stock_name} 主力突破吃貨，順勢做多！"
        if current_price < open_p and total_bid_vol > (total_ask_vol * 1.2) and recent_sell_cnt >= 3:
            return f"🎯【💥 做空訊號】{stock_name} 多頭防線潰散，順勢放空！"

    return f"⏳ 偵測中：未出現30秒內連續3筆精確大戶單 ({big_order_vol}張)，保持觀望
    # --- API 連線與測試模式控制機制 ---
if api_key or test_mode:
    client = RestClient(api_key=api_key) if api_key else None
    
    @st.fragment(run_every=2.0)
    def start_streaming(code):
        try:
            current_now = time.time()
            elapsed_speed = current_now - st.session_state.last_update_time
            if elapsed_speed > 10.0 or elapsed_speed <= 0: elapsed_speed = 2.00
            st.session_state.last_update_time = current_now

            if test_mode:
                taiex_price, taiex_change = 22135.45, -150.32
                otc_price, otc_change = 265.12, 1.45
                open_price = 29.00
                stock_name = "友達" if code == "2409" else f"股票 {code}"
                total_volume_lots = 95459
                trade_time = int(current_now * 1000)
                
                cycle = int(current_now) % 40
                
                if cycle < 10:
                    # 【階段 1：0~9秒】大戶外盤連續吃貨 ➔ 必定觸發【做多訊號】
                    raw_price = 29.05 + (cycle * 0.04) 
                    current_price = round(raw_price, 2)  # ⚡ 強制去除 Python 浮點數微小溢出誤差
                    tick_qty = 550  
                    tick_price = current_price
                    bids_base, asks_base = 1000, 5000  # 賣盤是買盤5倍，完美符合做多委託量比要求
                    last_bid, last_ask = round(current_price - 0.05, 2), current_price
                    
                elif cycle < 20:
                    # 【階段 2：10~19秒】高點折返下挫 ➔ 觸發【多頭清空熔斷】
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
                    tick_qty = 600  
                    tick_price = current_price
                    bids_base, asks_base = 6000, 1000  # 買盤是賣盤6倍，完美符合做空委託量比要求
                    last_bid, last_ask = current_price, round(current_price + 0.05, 2)
                    
                else:
                    # 【階段 4：30~39秒】止跌回升反彈 ➔ 觸發【空頭清空防嘎】
                    raw_price = 28.40 + ((cycle - 30) * 0.05)  
                    current_price = round(raw_price, 2)  
                    tick_qty = 0
                    tick_price = current_price
                    bids_base, asks_base = 2000, 2000
                    last_bid, last_ask = round(current_price - 0.05, 2), current_price

                bids = [{'price': round(current_price - 0.05 * i, 2), 'size': bids_base - i * 100} for i in range(1, 6)]
                asks = [{'price': round(current_price + 0.05 * i, 2), 'size': asks_base + i * 100} for i in range(1, 6)]
            else:
                if current_now - st.session_state.last_index_fetch_time > 30.0:
                    try:
                        tx_q = client.stock.intraday.quote(symbol='IX0001')
                        tx_p = tx_q.get('lastTrade', {}).get('price') or tx_q.get('closePrice') or 0.0
                        tx_ref = tx_q.get('referencePrice', tx_p)
                        st.session_state.taiex_cache = (tx_p, round(tx_p - tx_ref, 2))
                    except: pass
                    try:
                        otc_q = client.stock.intraday.quote(symbol='IX0043')
                        otc_p = otc_q.get('lastTrade', {}).get('price') or otc_q.get('closePrice') or 0.0
                        otc_ref = otc_q.get('referencePrice', otc_p)
                        st.session_state.otc_cache = (otc_p, round(otc_p - otc_ref, 2))
                    except: pass
                    st.session_state.last_index_fetch_time = current_now
                
                taiex_price, taiex_change = st.session_state.taiex_cache
                otc_price, otc_change = st.session_state.otc_cache
                
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
                bids, asks = quote.get('bids', []), quote.get('asks', [])
                while len(bids) < 5: bids.append({'price': 0.0, 'size': 0})
                while len(asks) < 5: asks.append({'price': 0.0, 'size': 0})
                
                last_trade = quote.get('lastTrade', {})
                tick_qty = int(last_trade.get('unit') or last_trade.get('size', 0))
                tick_price = last_trade.get('price', current_price)
                trade_time = last_trade.get('time', 0)
                last_bid = bids.get('price', 0.0) if bids else 0.0
                last_ask = asks.get('price', 0.0) if asks else 0.0

            if current_price == 0.0 and not test_mode:
                st.warning("⏳ 目前無即時成交數據...")
                return
            if st.session_state.open_price == 0.0:
                st.session_state.open_price = open_price
                
            tx_color = "#ff4466" if taiex_change >= 0 else "#00ff88"
            tx_sign = "+" if taiex_change > 0 else ""
            otc_color = "#ff4466" if otc_change >= 0 else "#00ff88"
            otc_sign = "+" if otc_change > 0 else ""
            
            index_html = f"<table style='width:100%; text-align:center; font-size:12px; margin-bottom:2px;'><tr><td style='width:49%; background-color:#161b22; padding:4px; border-radius:4px;'><span style='color:#888; font-size:10px;'>加權大盤</span><br><b style='color:{tx_color}; font-size:14px;'>{taiex_price:,.2f}</b> <span style='color:{tx_color}; font-size:10px;'>({tx_sign}{taiex_change})</span></td><td style='width:2%;'></td><td style='width:49%; background-color:#161b22; padding:4px; border-radius:4px;'><span style='color:#888; font-size:10px;'>櫃買指數</span><br><b style='color:{otc_color}; font-size:14px;'>{otc_price:,.2f}</b> <span style='color:{otc_color}; font-size:10px;'>({otc_sign}{otc_change})</span></td></tr></table>"
            index_block.markdown(index_html, unsafe_allow_html=True)

            dynamic_threshold = get_dynamic_big_order_threshold(current_price, total_volume_lots)
            mode_prefix = " (🌙測試中)" if test_mode else ""
            threshold_spot.caption(f"⚙️ 門檻: 單筆 {dynamic_threshold} 張 | 總量: {total_volume_lots:,} 張 | ⚡ {elapsed_speed:.2f} 秒/次{mode_prefix}")
            
            total_bid_vol = sum([b.get('size', 0) for b in bids])
            total_ask_vol = sum([a.get('size', 0) for a in asks])
            
            five_ticks_html = "<table style='width:100%; text-align:center; font-size:13px; border-collapse:collapse; font-family:monospace;'><tr style='background-color:#111; height:22px;'><th style='color:#00ff88; width:25%; font-size:11px;'>買張</th><th style='color:#00ff88; width:25%; font-size:11px;'>買價</th><th style='color:#ff4466; width:25%; font-size:11px;'>賣價</th><th style='color:#ff4466; width:25%; font-size:11px;'>賣張</th></tr>"
            for i in range(5):
                b_price = bids[i].get('price', 0.0)
                b_vol = int(bids[i].get('size', 0))
                a_price = asks[i].get('price', 0.0)
                a_vol = int(asks[i].get('size', 0))
                b_v_str = f"{b_vol:,}" if b_vol > 0 else "-"
                b_p_str = f"{b_price:.2f}" if b_price > 0 else "-"
                a_p_str = f"{a_price:.2f}" if a_price > 0 else "-"
                a_v_str = f"{a_vol:,}" if a_vol > 0 else "-"
                five_ticks_html += f"<tr style='height:24px; border-bottom:1px solid #1c1c1c;'><td style='color:#00ff88;'>{b_v_str}</td><td style='color:#00ff88; font-weight:bold;'>{b_p_str}</td><td style='color:#ff4466; font-weight:bold;'>{a_p_str}</td><td style='color:#ff4466;'>{a_v_str}</td></tr>"
            five_ticks_html += "</table>"
            five_ticks_spot.markdown(five_ticks_html, unsafe_allow_html=True)
            
            current_trade_key = (trade_time, tick_qty, tick_price)
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= max(dynamic_threshold, 150):
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
            
            decision = process_market_logic(current_price, total_bid_vol, total_ask_vol, dynamic_threshold, stock_name)
            if "做多" in decision: signal_spot.success(decision)
            elif "做空" in decision: signal_spot.error(decision)
            else: signal_spot.info(decision)
                
        except FugleAPIError as e:
            if "Rate limit exceeded" in str(e):
                st.error("🚨 偵測到富果限制頻率，系統正在自動降速防守中...")
                time.sleep(5)
            else: st.error(f"富果 API 錯誤: {e}")
        except Exception as e: st.error(f"連線異常: {e}")

    start_streaming(stock_code)
else:
    st.warning("🔑 請先展開上方選單輸入「富果 API Key」或勾選「模擬測試」以啟動功能。")
