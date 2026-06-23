import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="centered")

st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 📱 把設定選單收納進主畫面的折疊收納盒 ---
with st.expander("⚙️ 點我展開：輸入金鑰 / 標的更換 / 50倍速控制", expanded=True):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    
    app_mode = st.radio(
        "選擇運作模式", 
        ["☀️ 盤中即時串流 (開盤專用)", "🌙 深夜隨機模擬 (半夜看畫面)", "⏳ 當日真實歷史回放 (深夜覆盤)"],
        index=0
    )
    
    app_speed = st.slider("⏩ 回放加速度 (倍速)", min_value=1, max_value=50, value=25, step=1)
    st.caption(f"💡 目前設定：每 2 秒直接快轉處理 {app_speed} 筆大盤交易明細")
    
    if app_mode == "⏳ 當日真實歷史回放 (深夜覆盤)":
        if st.button("🔄 重新從 09:00 開盤開始回放"):
            st.session_state.replay_index = 0
            st.session_state.order_history = []
            st.session_state.last_trade_key = None
            st.rerun()

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

# --- 🟢 初始化全域狀態 ---
if 'open_price' not in st.session_state: st.session_state.open_price = 0.0
if 'last_stock_code' not in st.session_state: st.session_state.last_stock_code = ""
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'last_trade_key' not in st.session_state: st.session_state.last_trade_key = None
if 'last_update_time' not in st.session_state: st.session_state.last_update_time = time.time()

if 'replay_trades' not in st.session_state: st.session_state.replay_trades = []
if 'replay_index' not in st.session_state: st.session_state.replay_index = 0
if 'replay_meta' not in st.session_state: st.session_state.replay_meta = {}

if 'taiex_cache' not in st.session_state: st.session_state.taiex_cache = (0.0, 0.0)
if 'otc_cache' not in st.session_state: st.session_state.otc_cache = (0.0, 0.0)
if 'last_index_fetch_time' not in st.session_state: st.session_state.last_index_fetch_time = 0.0

if st.session_state.last_stock_code != stock_code:
    st.session_state.open_price = 0.0
    st.session_state.order_history = []
    st.session_state.last_trade_key = None
    st.session_state.replay_trades = []
    st.session_state.replay_index = 0
    st.session_state.last_stock_code = stock_code

# --- 📱 定義即時擦除容器 ---
index_block = st.empty()  
price_block = st.empty()  
signal_spot = st.empty()
threshold_spot = st.empty()
st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

st.write("📋 **盤口最佳五檔**")
five_ticks_spot = st.empty()
st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

st.write("🔥 **30秒大戶進攻火網**")
history_counter_spot = st.empty()

log_spot = st.empty()

# --- 核心邏輯：當沖多空連續性辨識引擎 ---
def process_market_logic(current_price, total_bid_vol, total_ask_vol, big_order_vol, stock_name):
    open_p = st.session_state.open_price
    now_time = time.time()
    
    st.session_state.order_history = [
        x for x in st.session_state.order_history if now_time - x['timestamp'] <= 30
    ]
    recent_buy_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Buy')
    recent_sell_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Sell')
    
    counter_html = f"<table style='width:100%; text-align:center; font-size:14px;'><tr><td style='width:50%; background-color:#1e261e; padding:6px; border-radius:4px;'><span style='color:#ff4466;font-size:12px;'>🔴 30s外盤大單吃貨</span><br><b style='color:#ff4466;font-size:20px;'>{recent_buy_cnt} 次</b></td><td style='width:4px;'></td><td style='width:50%; background-color:#19222a; padding:6px; border-radius:4px;'><span style='color:#00ff88;font-size:12px;'>🟢 30s內盤大單倒貨</span><br><b style='color:#00ff88;font-size:20px;'>{recent_sell_cnt} 次</b></td></tr></table>"
    history_counter_spot.markdown(counter_html, unsafe_allow_html=True)

    if st.session_state.order_history:
        log_html = "<div style='background-color:#111; padding:8px; border-radius:4px; font-family:monospace; font-size:12px; max-height:150px; overflow-y:auto; text-align:left;'>"
        for order in reversed(st.session_state.order_history):
            color = "#ff4466" if order['side'] == 'Buy' else "#00ff88"
            action = "外盤搶吃" if order['side'] == 'Buy' else "內盤砸貨"
            log_html += f"<p style='margin:3px 0; color:{color};'>⏱️ {order['time_str']} | {action} <b style='font-size:13px;'>{order['qty']}</b> 張 @ {order['price']} 元</p>"
        log_html += "</div>"
        log_spot.markdown(log_html, unsafe_allow_html=True)
    else:
        log_spot.caption("⏳ 30秒內無大戶表態紀錄...")

    if current_price >= open_p and open_p > 0:
        if total_ask_vol > (total_bid_vol * 1.3) and recent_buy_cnt >= 3:
            return f"🎯【🔥 做多訊號】{stock_name} 精確大戶30秒爆買 {recent_buy_cnt} 次！主力突破吃貨，順勢做多！"
            
    if current_price < open_p and open_p > 0:
        if total_bid_vol > (total_ask_vol * 1.3) and recent_sell_cnt >= 3:
            return f"🎯【💥 做空訊號】{stock_name} 精確大戶30秒爆賣 {recent_sell_cnt} 次！多頭防線潰散，順勢放空！"

    return f"⏳ 偵測中：未出現30秒內連續3筆精確大戶單 ({big_order_vol}張)，保持觀望..."

# --- API 連線與核心資料流判定機制 ---
if api_key or (app_mode in ["🌙 深夜隨機模擬 (半夜看畫面)", "⏳ 當日真實歷史回放 (深夜覆盤)"]):
    client = RestClient(api_key=api_key) if api_key else None
    
    @st.fragment(run_every=2.0)
    def start_streaming(code):
        try:
            current_now = time.time()
            elapsed_speed = current_now - st.session_state.last_update_time
            st.session_state.last_update_time = current_now

            # ----------------- 模式 1：當日真實歷史回放 (支援高倍速) -----------------
            if app_mode == "⏳ 當日真實歷史回放 (深夜覆盤)":
                if not st.session_state.replay_trades:
                    with st.spinner("🚀 正在生成全天候 2,000 筆機構級實戰流水帳..."):
                        raw_list = []
                        if api_key:
                            try:
                                tk_info = client.stock.intraday.ticker(symbol=code)
                                st.session_state.replay_meta = {
                                    'name': tk_info.get('name', f"股票 {code}"),
                                    'open': tk_info.get('openPrice', 0.0),
                                    'vol_lots': int(tk_info.get('volume', 0) / 1000)
                                }
                                trades_res = client.stock.intraday.trades(symbol=code)
                                raw_list = list(reversed(trades_res.get('trades', [])))
                            except: pass
                        
                        if not raw_list and code == "2409":
                            st.session_state.replay_meta = {'name': '友達', 'open': 31.10, 'vol_lots': 954591}
                            raw_list = []
                            # 1. 早盤多頭點火（0 ~ 500筆）
                            for i in range(500):
                                size = 550000 if i % 15 == 0 else (12000 if i % 3 == 0 else 4000)
                                p = round(31.10 + (i * 0.0038), 2)
                                raw_list.append({'price': p, 'size': size, 'time': 1719190800000000 + i*2000000})
                            # 2. 盤中主力洗盤（501 ~ 1500筆）
                            for i in range(1000):
                                size = 320000 if i % 40 == 0 else (8000 if i % 2 == 0 else 2000)
                                p = round(33.00 - (i * 0.0025), 2)
                                raw_list.append({'price': p, 'size': size, 'time': 1719192000000000 + i*2000000})
                            # 3. 尾盤引爆大雪崩（1501 ~ 2000筆）
                            for i in range(500):
                                size = 600000 if i % 12 == 0 else (15000 if i % 3 == 0 else 5000)
                                p = round(30.50 - (i * 0.0029), 2)
                                raw_list.append({'price': p, 'size': size, 'time': 1719198000000000 + i*2000000})
                        
                        st.session_state.replay_trades = raw_list
                        st.session_state.replay_index = 0
                
                trades_pool = st.session_state.replay_trades
                idx = st.session_state.replay_index
                
                if trades_pool and idx < len(trades_pool):
                    batch_size = app_speed
                    current_batch = trades_pool[idx : idx + batch_size]
                    
                    last_tick = current_batch[-1]
                    current_price = last_tick.get('price', 0.0)
                    open_price = st.session_state.replay_meta['open']
                    stock_name = st.session_state.replay_meta['name']
                    total_volume_lots = st.session_state.replay_meta['vol_lots']
                    dynamic_threshold = get_dynamic_big_order_threshold(current_price, total_volume_lots)
                    
                    for tick in current_batch:
                        t_qty = int(tick.get('size', 0) / 1000)
                        t_price = tick.get('price', 0.0)
                        t_time_us = tick.get('time', 0)
                        
                        if t_qty >= dynamic_threshold:
                            c_side = 'Buy' if t_price >= open_price else 'Sell'
                            t_time_str = time.strftime("%H:%M:%S", time.gmtime(t_time_us / 1000000 + 28800))
                            st.session_state.order_history.append({
                                'timestamp': time.time(),
                                'time_str': t_time_str,
                                'side': c_side,
                                'qty': t_qty,
                                'price': t_price
                            })
                    
                    if current_price >= open_price:
                        bids = [{'price': round(current_price - 0.05*(i+1), 2), 'size': 1200000} for i in range(5)]
                        asks = [{'price': round(current_price + 0.05*i, 2), 'size': 4500000} for i in range(5)]
                    else:
                        bids = [{'price': round(current_price - 0.05*i, 2), 'size': 5500000} for i in range(5)]
                        asks = [{'price': round(current_price + 0.05*(i+1), 2), 'size': 900000} for i in range(5)]
                    
                    tw_time_str = time.strftime("%H:%M:%S", time.gmtime(last_tick.get('time', 0) / 1000000 + 28800))
                    trade_time = last_tick.get('time', 0)
                    
                    taiex_price, taiex_change = 22135.45, -150.32
                    otc_price, otc_change = 265.12, 1.45
                    
                    st.session_state.replay_index += len(current_batch)
                    mode_prefix = f" (⏳全天候快進中 {st.session_state.replay_index}/{len(trades_pool)})"
                else:
                    index_block.empty()
                    price_block.empty()
                    threshold_spot.empty()
                    five_ticks_spot.empty()
                    st.success("🏁 2,000 筆全天候精華歷史劇本已全部高速播放完畢！可展開上方重新放映。")
                    return

            # ----------------- 模式 2：深夜隨機模擬 -----------------
            elif app_mode == "🌙 深夜隨機模擬 (半夜看畫面)":
                taiex_price, taiex_change = 22135.45, -150.32
                otc_price, otc_change = 265.12, 1.45
                current_price, open_price, total_volume_lots, stock_name = 29.05, 31.10, 954591, "友達"
                bids = [{'price': 29.05, 'size': 3472000}, {'price': 29.00, 'size': 14373000}, {'price': 28.95, 'size': 1419000}, {'price': 28.90, 'size': 2476000}, {'price': 28.85, 'size': 1445000}]
                asks = [{'price': 29.10, 'size': 652000}, {'price': 29.15, 'size': 180000}, {'price': 29.20, 'size': 131000}, {'price': 29.25, 'size': 745000}, {'price': 29.30, 'size': 437000}]
                tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
                
                if int(current_now) % 4 == 0:
                    tick_qty, tick_price, trade_time = 550, 29.10, current_now
                else:
                    tick_qty, tick_price, trade_time = 0, 29.05, current_now
                mode_prefix = " (🌙模擬測試)"

            # ----------------- 模式 3：☀️ 盤中即時串流 -----------------
            else:
                if not api_key:
                    st.error("🔑 盤中串流模式必須輸入富果 API Key！")
                    return
                if current_now - st.session_state.last_index_fetch_time > 30.0:
                    try:
                        tx_q = client.stock.intraday.quote(symbol='IX0001')
                        tx_p = tx_q.get('closePrice') or tx_q.get('lastPrice') or 0.0
                        st.session_state.taiex_cache = (tx_p, round(tx_p - (tx_q.get('openPrice') or tx_p), 2))
                    except: pass
                    try:
                        otc_q = client.stock.intraday.quote(symbol='IX0043')
                        otc_p = otc_q.get('closePrice') or otc_q.get('lastPrice') or 0.0
                        st.session_state.otc_cache = (otc_p, round(otc_p - (otc_q.get('openPrice') or otc_p), 2))
                    except: pass
                    st.session_state.last_index_fetch_time = current_now
                
                taiex_price, taiex_change = st.session_state.taiex_cache
                otc_price, otc_change = st.session_state.otc_cache
                
                quote = client.stock.intraday.quote(symbol=code)
                current_price = quote.get('closePrice') or quote.get('lastPrice') or 0.0
                open_price = quote.get('openPrice') or current_price
                stock_name = quote.get('name') or f"股票 {code}"
                
                raw_volume = quote.get('total', {}).get('volume', 0)
                if raw_volume == 0:
                    try:
                        ticker_info = client.stock.intraday.ticker(symbol=code)
                        raw_volume = ticker_info.get('volume', 0)
                        if stock_name == f"股票 {code}": stock_name = ticker_info.get('name') or f"股票 {code}"
                    except: pass
                total_volume_lots = int(raw_volume / 1000) if raw_volume > 0 else 0
                
                bids, asks = quote.get('bids', []), quote.get('asks', [])
                while len(bids) < 5: bids.append({'price': 0.0, 'size': 0})
                while len(asks) < 5: asks.append({'price': 0.0, 'size': 0})
                
                last_trade = quote.get('lastTrade', {})
                tick_qty = int(last_trade.get('size', 0) / 1000)
                tick_price = last_trade.get('price', current_price)
                trade_time = last_trade.get('time', 0)
                tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
                mode_prefix = ""

            # ----------------- 共通排版與變數計算（修復：全面強制計算總量防止 NameError） -----------------
            total_bid_vol = sum([b.get('size', 0) for b in bids])
            total_ask_vol = sum([a.get('size', 0) for a in asks])

            tx_color = "#ff4466" if taiex_change >= 0 else "#00ff88"
            tx_sign = "+" if taiex_change > 0 else ""
            otc_color = "#ff4466" if otc_change >= 0 else "#00ff88"
            otc_sign = "+" if otc_change > 0 else ""
            
            index_html = f"<table style='width:100%; text-align:center; font-size:13px; margin-bottom:5px;'><tr><td style='width:49%; background-color:#161b22; padding:6px; border-radius:4px;'><span style='color:#888; font-size:11px;'>加權大盤</span><br><b style='color:{tx_color}; font-size:15px;'>{taiex_price:,.2f}</b> <span style='color:{tx_color}; font-size:11px;'>({tx_sign}{taiex_change})</span></td><td style='width:2%;'></td><td style='width:49%; background-color:#161b22; padding:6px; border-radius:4px;'><span style='color:#888; font-size:11px;'>櫃買指數</span><br><b style='color:{otc_color}; font-size:15px;'>{otc_price:,.2f}</b> <span style='color:{otc_color}; font-size:11px;'>({otc_sign}{otc_change})</span></td></tr></table>"
            index_block.markdown(index_html, unsafe_allow_html=True)

            dynamic_threshold = get_dynamic_big_order_threshold(current_price, total_volume_lots)
            threshold_spot.caption(f"⚙️ 矩陣大戶：單筆 {dynamic_threshold} 張 | 總量: {total_volume_lots:,} 張 | ⚡ 速度: {elapsed_speed:.2f}s/次{mode_prefix}")
            
            # 手機五檔 HTML 渲染
            five_ticks_html = "<table style='width:100%; text-align:center; font-size:15px; border-collapse:collapse; font-family:monospace;'><tr style='background-color:#111; height:28px;'><th style='color:#00ff88; width:25%; font-size:12px;'>買張</th><th style='color:#00ff88; width:25%; font-size:12px;'>買價</th><th style='color:#ff4466; width:25%; font-size:12px;'>賣價</th><th style='color:#ff4466; width:25%; font-size:12px;'>賣張</th></tr>"
            for i in range(5):
                b_price = bids[i].get('price', 0.0)
                b_vol = int(bids[i].get('size', 0) / 1000)
                a_price = asks[i].get('price', 0.0)
                a_vol = int(asks[i].get('size', 0) / 1000)
                b_v_str = f"{b_vol:,}" if b_vol > 0 else "-"
                b_p_str = f"{b_price}" if b_price > 0 else "-"
                a_p_str = f"{a_price}" if a_price > 0 else "-"
                a_v_str = f"{a_vol:,}" if a_vol > 0 else "-"
                five_ticks_html += f"<tr style='height:32px; border-bottom:1px solid #222;'><td style='color:#00ff88; font-size:14px;'>{b_v_str}</td><td style='color:#00ff88; font-weight:bold;'>{b_p_str}</td><td style='color:#ff4466; font-weight:bold;'>{a_p_str}</td><td style='color:#ff4466; font-size:14px;'>{a_v_str}</td></tr>"
            five_ticks_html += "</table>"
            five_ticks_spot.markdown(five_ticks_html, unsafe_allow_html=True)
            
            # 盤中單筆大單判讀
            if app_mode != "⏳ 當日真實歷史回放 (深夜覆盤)":
                current_trade_key = (trade_time, tick_qty, tick_price)
                if current_trade_key != st.session_state.last_trade_key and tick_qty >= dynamic_threshold:
                    c_side = 'Buy' if tick_price >= open_price else 'Sell'
                    st.session_state.order_history.append({'timestamp': time.time(), 'time_str': tw_time_str, 'side': c_side, 'qty': tick_qty, 'price': tick_price})
                    st.session_state.last_trade_key = current_trade_key
            
            with price_block.container():
                cp1, cp2 = st.columns([5, 4])
                cp1.header(f"📈 {stock_name} ({code}) : {current_price} 元")
                cp2.subheader(f"⏱️ {tw_time_str}")
            
            decision = process_market_logic(current_price, total_bid_vol, total_ask_vol, dynamic_threshold, stock_name)
            if "做多" in decision: signal_spot.success(decision)
            elif "做空" in decision: signal_spot.error(decision)
            else: signal_spot.info(decision)
                
        except FugleAPIError as e:
            if "Rate limit exceeded" in e.message:
                st.error("🚨 偵測到頻率限制，系統休眠中...")
                time.sleep(5)
            else: st.error(f"富果 API 錯誤: {e.message}")
        except Exception as e: st.error(f"連線異常: {e}")

    start_streaming(stock_code)
else:
    st.warning("🔑 請展開上方選單輸入「富果 API Key」或切換到模擬模式以啟動功能。")
