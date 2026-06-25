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

# --- 📱 設定選單 ---
with st.expander("⚙️ 設定：輸入金鑰 / 更換股票", expanded=False):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        manual_big_order_lots = st.number_input("🔥 大戶定義 (張)", min_value=1, max_value=5000, value=150, step=10)
    with col_u2:
        manual_ratio = st.number_input("📊 參考量比 (倍)", min_value=1.0, max_value=5.0, value=1.2, step=0.1, format="%.1f")
    test_mode = st.checkbox("🌙 啟動深夜模擬測試 (半夜看畫面專用)", value=False)

# --- 📱 定義 UI 容器鎖定 ---
alert_spot = st.empty()          # 進階濾網警告區
price_block = st.empty()         # 價格與大盤狀態區
threshold_spot = st.empty()      # 資訊與量比狀態區
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:14px; color:#ddd;'>📋 盤口最佳五檔</b>", unsafe_allow_html=True)
five_ticks_spot = st.empty()
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:14px; color:#ddd;'>🔥 多空動能燈號</b>", unsafe_allow_html=True)
signal_spot = st.empty()

st.markdown("<b style='font-size:14px; color:#ddd;'>📜 大戶進攻即時紀錄</b>", unsafe_allow_html=True)
log_spot = st.empty()

# --- 🟢 初始化全域狀態機制 ---
def init_session_state():
    defaults = {
        'open_price': 0.0, 'hod': 0.0, 'lod': 999999.0, 
        'order_history': [], 'last_trade_key': None, 
        'last_stock_code': "", 'last_market_update': 0, 
        'market_trend': "⚪ 大盤震盪", 'last_bids_vol': 0, 'last_asks_vol': 0
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if st.session_state.last_stock_code != stock_code:
        for key in defaults.keys():
            st.session_state[key] = defaults[key]
        st.session_state.last_stock_code = stock_code

init_session_state()

# --- 核心邏輯：當沖多空連續性辨識引擎 ---
def process_market_logic(current_price, vwap):
    now_time = time.time()
    # 清理 30 秒前的歷史紀錄
    st.session_state.order_history = [
        x for x in st.session_state.order_history if now_time - x['timestamp'] <= 30
    ]
    
    recent_buy_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Buy')
    recent_sell_cnt = sum(1 for x in st.session_state.order_history if x['side'] == 'Sell')

    if recent_buy_cnt > recent_sell_cnt:
        if current_price > vwap:
            return "🔥 突破均價！大戶連續外盤掃貨中，適合順勢做多"
        else:
            return "⚠️ 大戶買進，但股價仍在均價之下，注意抄底風險"
    elif recent_sell_cnt > recent_buy_cnt:
        if current_price < vwap:
            return "🧊 跌破均價！大戶連續內盤砸貨，適合順勢做空"
        else:
            return "⚠️ 大戶賣出，但股價有撐，可能是假跌破"
    else:
        return "⚖️ 目前多空交戰或無大單進出，建議觀望"

# --- 核心主迴圈 ---
def start_streaming(code):
    if not api_key and not test_mode:
        return
        
    client = RestClient(api_key=api_key) if not test_mode else None

    while True:
        try:
            start_time = time.time()
            alerts = []
            
            if test_mode:
                # 模擬測試邏輯 (可自行擴充)
                current_price, open_price, stock_name = 28.5, 28.0, "測試股"
                tick_qty, tick_price = 200, 28.5
                bids = [{'price': 28.45, 'size': 1500}] * 5
                asks = [{'price': 28.50, 'size': 1200}] * 5
                vwap = 28.3
                trade_time = time.time()
            else:
                # 1. 抓取大盤資訊 (每 60 秒一次)
                if start_time - st.session_state.last_market_update > 60:
                    try:
                        m_quote = client.stock.intraday.quote(symbol="IX0001")
                        m_price = m_quote.get('lastTrade', {}).get('price', 0)
                        m_open = m_quote.get('priceOpen', 0)
                        if m_price > m_open: st.session_state.market_trend = "🟢 大盤順風"
                        elif m_price < m_open: st.session_state.market_trend = "🔴 大盤逆風"
                        st.session_state.last_market_update = start_time
                    except: pass

                # 2. 抓取個股資訊
                quote = client.stock.intraday.quote(symbol=code)
                current_price = quote.get('lastTrade', {}).get('price') or quote.get('closePrice') or 0.0
                open_price = quote.get('priceOpen') or quote.get('openPrice') or current_price
                stock_name = quote.get('name') or f"股票 {code}"
                
                # 計算 VWAP
                total_info = quote.get('total', {})
                total_vol = total_info.get('tradeVolume', 0)
                total_val = total_info.get('tradeValue', 0)
                vwap = (total_val / total_vol) if total_vol > 0 else current_price
                
                bids = quote.get('bids', [])
                asks = quote.get('asks', [])
                while len(bids) < 5: bids.append({'price': 0.0, 'size': 0})
                while len(asks) < 5: asks.append({'price': 0.0, 'size': 0})

                last_trade = quote.get('lastTrade', {})
                tick_qty = int(last_trade.get('size', 0))
                tick_price = last_trade.get('price', current_price)
                trade_time = last_trade.get('time', 0)

            if current_price == 0.0:
                continue

            if st.session_state.open_price == 0.0: st.session_state.open_price = open_price
            
            # --- HOD / LOD 追蹤 ---
            if current_price > st.session_state.hod and st.session_state.hod != 0:
                alerts.append(f"🔥 突破今日新高: {current_price:.2f}")
            if current_price < st.session_state.lod and st.session_state.lod != 999999.0:
                alerts.append(f"🧊 跌破今日新低: {current_price:.2f}")
            st.session_state.hod = max(st.session_state.hod, current_price)
            st.session_state.lod = min(st.session_state.lod, current_price)

            # --- 五檔抽單偵測 ---
            total_bid_vol = sum([b.get('size', 0) for b in bids if isinstance(b, dict)])
            total_ask_vol = sum([a.get('size', 0) for a in asks if isinstance(a, dict)])
            
            if st.session_state.last_bids_vol > 0 and (st.session_state.last_bids_vol - total_bid_vol) > 500:
                alerts.append("🚨 買盤異常撤單，當心支撐是假的！")
            if st.session_state.last_asks_vol > 0 and (st.session_state.last_asks_vol - total_ask_vol) > 500:
                alerts.append("🚨 賣盤異常撤單，上方壓力可能減輕！")
                
            st.session_state.last_bids_vol = total_bid_vol
            st.session_state.last_asks_vol = total_ask_vol

            # 🐞 [Bug Fix] 正確取得內外盤比對基準
            last_bid = bids[0].get('price', 0.0) if isinstance(bids, list) and len(bids) > 0 else 0.0
            last_ask = asks[0].get('price', 0.0) if isinstance(asks, list) and len(asks) > 0 else 0.0

            # --- 畫面渲染 ---
            tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
            p_diff = current_price - st.session_state.open_price
            p_color = "#ff4466" if p_diff >= 0 else "#00ff88"
            
            price_block.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom: 2px;'>"
                f"<span style='font-size:16px; font-weight:bold;'>📈 {stock_name} ({code})</span>"
                f"<span style='font-size:18px; font-weight:bold; color:{p_color};'>{current_price:.2f} </span>"
                f"</div>"
                f"<div style='font-size:12px; color:#aaa;'>大盤: {st.session_state.market_trend} | 均價線 (VWAP): {vwap:.2f} | 時間: {tw_time_str}</div>", 
                unsafe_allow_html=True
            )

            # 五檔表格渲染 (略為簡化排版)
            five_ticks_html = "<table style='width:100%; text-align:center; font-size:13px; border-collapse:collapse;'><tr style='background-color:#111; height:22px;'><th style='color:#00ff88;'>買張</th><th style='color:#00ff88;'>買價</th><th style='color:#ff4466;'>賣價</th><th style='color:#ff4466;'>賣張</th></tr>"
            for i in range(5):
                b_p = bids[i].get('price', 0.0) if isinstance(bids[i], dict) else 0.0
                b_v = bids[i].get('size', 0) if isinstance(bids[i], dict) else 0
                a_p = asks[i].get('price', 0.0) if isinstance(asks[i], dict) else 0.0
                a_v = asks[i].get('size', 0) if isinstance(asks[i], dict) else 0
                five_ticks_html += f"<tr style='border-bottom:1px solid #1c1c1c;'><td style='color:#00ff88;'>{b_v if b_v>0 else '-'}</td><td style='color:#00ff88;'>{b_p if b_p>0 else '-'}</td><td style='color:#ff4466;'>{a_p if a_p>0 else '-'}</td><td style='color:#ff4466;'>{a_v if a_v>0 else '-'}</td></tr>"
            five_ticks_html += "</table>"
            five_ticks_spot.markdown(five_ticks_html, unsafe_allow_html=True)

            # --- 大戶明細捕捉 ---
            current_trade_key = (trade_time, tick_qty, tick_price)
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= manual_big_order_lots:
                if tick_price >= last_ask and last_ask > 0:
                    current_side = 'Buy'  # 外盤
                elif tick_price <= last_bid and last_bid > 0:
                    current_side = 'Sell' # 內盤
                else:
                    current_side = 'Buy' if tick_price >= vwap else 'Sell' # 用 VWAP 當備用防線取代開盤價
                    
                st.session_state.order_history.insert(0, {
                    'timestamp': time.time(), 'time_str': tw_time_str, 
                    'side': current_side, 'qty': tick_qty, 'price': tick_price
                })
                st.session_state.last_trade_key = current_trade_key
            
            # --- 警報與紀錄渲染 ---
            if alerts:
                alert_html = "".join([f"<div style='color:#ffa500; font-size:12px; margin-bottom:2px;'>{a}</div>" for a in alerts])
                alert_spot.markdown(alert_html, unsafe_allow_html=True)
            else:
                alert_spot.empty()

            decision = process_market_logic(current_price, vwap)
            signal_spot.markdown(f"<div style='padding:8px; border-radius:4px; background-color:#1c1c1c; color:#fff; font-size:13px;'>{decision}</div>", unsafe_allow_html=True)

            log_html = ""
            for item in st.session_state.order_history[:5]: # 只顯示近5筆
                color = "#ff4466" if item['side'] == 'Buy' else "#00ff88"
                action = "外盤買進" if item['side'] == 'Buy' else "內盤賣出"
                log_html += f"<div style='color:{color}; font-size:13px;'>{item['time_str']} | {item['price']} | {item['qty']}張 ({action})</div>"
            log_spot.markdown(log_html, unsafe_allow_html=True)

        except FugleAPIError as e:
            st.error("🚨 API 異常，冷卻中...")
            time.sleep(2)
        except Exception as e:
            st.error(f"系統錯誤: {e}")
            
        time.sleep(2) # 2秒循環確保不超頻

if api_key or test_mode:
    start_streaming(stock_code)
else:
    st.warning("🔑 請先展開上方選單輸入「富果 API Key」以啟動功能。")
