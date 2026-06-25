import streamlit as st
import pandas as pd
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 📱 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="wide")
st.markdown("""
    <style>
    .block-container {padding-top: 0.5rem; padding-bottom: 0.5rem; max-width: 100% !important;}
    h1 {font-size: 22px !important; margin-bottom: 5px !important;}
    hr {margin: 8px 0 !important;}
    p, span, label {font-size: 14px !important;}
    </style>
""", unsafe_allow_html=True)

# --- 📱 左側側邊欄設定選單 (更換股票 / 輸入金鑰) ---
with st.sidebar:
    st.header("⚡ 系統設定選單")
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        manual_big_order_lots = st.number_input("🔥 大戶定義 (張)", min_value=1, max_value=5000, value=150, step=10)
    with col_u2:
        manual_ratio = st.number_input("📊 參考量比 (倍)", min_value=1.0, max_value=5.0, value=1.2, step=0.1, format="%.1f")
    test_mode = st.checkbox("🌙 啟動深夜模擬測試", value=False)

# --- 📱 頂部固定狀態提示區 (防止右下角遮擋) ---
if not api_key and not test_mode:
    st.warning("🔑 請先展開左側側邊欄輸入「富果 API Key」以啟動功能。")
    st.stop()

# --- 📱 定義 UI 主畫面容器鎖定 ---
price_block = st.empty()         # 大幅放大：價格與大盤狀態區
signal_spot = st.empty()         # 多空動能燈號狀態區
alert_spot = st.empty()          # 進階濾網警告區
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:16px; color:#ddd;'>📋 盤口最佳五檔</b>", unsafe_allow_html=True)
five_ticks_spot = st.empty()
st.markdown("<hr>", unsafe_allow_html=True)

st.markdown("<b style='font-size:16px; color:#ddd;'>📜 大戶進攻即時紀錄</b>", unsafe_allow_html=True)
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
                current_price, open_price, stock_name = 30.40, 30.0, "測試友達"
                tick_qty, tick_price = 200, 30.40
                bids = [{'price': 30.40 - i*0.05, 'size': 1000 + i*150} for i in range(5)]
                asks = [{'price': 30.45 + i*0.05, 'size': 1200 + i*200} for i in range(5)]
                vwap = 30.25
                trade_time = time.time()
            else:
                if start_time - st.session_state.last_market_update > 60:
                    try:
                        m_quote = client.stock.intraday.quote(symbol="IX0001")
                        m_price = m_quote.get('lastTrade', {}).get('price', 0)
                        m_open = m_quote.get('priceOpen', 0)
                        if m_price > m_open: st.session_state.market_trend = "🟢 大盤順風"
                        elif m_price < m_open: st.session_state.market_trend = "🔴 大盤逆風"
                        st.session_state.last_market_update = start_time
                    except: pass

                quote = client.stock.intraday.quote(symbol=code)
                current_price = quote.get('lastTrade', {}).get('price') or quote.get('closePrice') or 0.0
                open_price = quote.get('priceOpen') or quote.get('openPrice') or current_price
                stock_name = quote.get('name') or f"股票 {code}"
                
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
            
            if current_price > st.session_state.hod and st.session_state.hod != 0:
                alerts.append(f"🔥 突破今日新高: {current_price:.2f}")
            if current_price < st.session_state.lod and st.session_state.lod != 999999.0:
                alerts.append(f"🧊 跌破今日新低: {current_price:.2f}")
            st.session_state.hod = max(st.session_state.hod, current_price)
            st.session_state.lod = min(st.session_state.lod, current_price)

            total_bid_vol = sum([b.get('size', 0) for b in bids if isinstance(b, dict)])
            total_ask_vol = sum([a.get('size', 0) for a in asks if isinstance(a, dict)])
            
            if st.session_state.last_bids_vol > 0 and (st.session_state.last_bids_vol - total_bid_vol) > 500:
                alerts.append("🚨 買盤異常撤單，當心支撐是假的！")
            if st.session_state.last_asks_vol > 0 and (st.session_state.last_asks_vol - total_ask_vol) > 500:
                alerts.append("🚨 賣盤異常撤單，上方壓力可能減輕！")
                
            st.session_state.last_bids_vol = total_bid_vol
            st.session_state.last_asks_vol = total_ask_vol

            last_bid = bids[0].get('price', 0.0) if isinstance(bids, list) and len(bids) > 0 else 0.0
            last_ask = asks[0].get('price', 0.0) if isinstance(asks, list) and len(asks) > 0 else 0.0

            # --- 畫面渲染：放大顯示區 ---
            tw_time_str = time.strftime("%H:%M:%S", time.gmtime(time.time() + 28800))
            p_diff = current_price - st.session_state.open_price
            p_color = "#ff4466" if p_diff >= 0 else "#00ff88"
            
            price_block.markdown(
                f"<div style='background-color: #1E1E1E; padding: 18px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #333;'>"
                f"  <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;'>"
                f"    <span style='font-size:26px; font-weight:bold; color:white;'>📈 {stock_name} ({code})</span>"
                f"    <span style='font-size:34px; font-weight:bold; color:{p_color};'>{current_price:.2f}</span>"
                f"  </div>"
                f"  <div style='font-size:15px; color:#ccc; border-top: 1px solid #444; padding-top: 10px;'>"
                f"    大盤: {st.session_state.market_trend} &nbsp;|&nbsp; 均價線 (VWAP): <b style='color:#fff;'>{vwap:.2f}</b> &nbsp;|&nbsp; 時間: {tw_time_str}"
                f"  </div>"
                f"</div>", 
                unsafe_allow_html=True
            )

            # ==========================================
            # ✨ 核心修正：改回原生漂亮的 DataFrame，並精準控制小數點
            # ==========================================
            df_5_ticks = pd.DataFrame({
                "買張": [b.get('size', 0) if isinstance(b, dict) else 0 for b in bids],
                "買價": [b.get('price', 0.0) if isinstance(b, dict) else 0.0 for b in bids],
                "賣價": [a.get('price', 0.0) if isinstance(a, dict) else 0.0 for a in asks],
                "賣張": [a.get('size', 0) if isinstance(a, dict) else 0 for a in asks]
            })

            # 自訂格式化函數 (沒有掛單顯示 '-'，有掛單強制顯示兩位小數)
            def format_price(val): return f"{val:.2f}" if val > 0 else "-"
            def format_size(val): return f"{int(val)}" if val > 0 else "-"

            styled_df = df_5_ticks.style\
                .format({
                    '買價': format_price, 
                    '賣價': format_price,
                    '買張': format_size,
                    '賣張': format_size
                })\
                .map(lambda x: 'color: #00ff88; font-weight: bold;', subset=['買張', '買價'])\
                .map(lambda x: 'color: #ff4466; font-weight: bold;', subset=['賣價', '賣張'])

            # 注入回原本的表格位置
            five_ticks_spot.dataframe(styled_df, use_container_width=True, hide_index=True)
            # ==========================================

            # --- 大戶明細捕捉 ---
            current_trade_key = (trade_time, tick_qty, tick_price)
            if current_trade_key != st.session_state.last_trade_key and tick_qty >= manual_big_order_lots:
                if tick_price >= last_ask and last_ask > 0:
                    current_side = 'Buy'
                elif tick_price <= last_bid and last_bid > 0:
                    current_side = 'Sell'
                else:
                    current_side = 'Buy' if tick_price >= vwap else 'Sell'
                    
                st.session_state.order_history.insert(0, {
                    'timestamp': time.time(), 'time_str': tw_time_str, 
                    'side': current_side, 'qty': tick_qty, 'price': tick_price
                })
                st.session_state.last_trade_key = current_trade_key
            
            # --- 警報與紀錄渲染 ---
            if alerts:
                alert_html = "".join([f"<div style='color:#ffa500; font-size:13px; margin-bottom:2px;'>{a}</div>" for a in alerts])
                alert_spot.markdown(alert_html, unsafe_allow_html=True)
            else:
                alert_spot.empty()

            decision = process_market_logic(current_price, vwap)
            signal_spot.markdown(f"<div style='padding:10px; border-radius:6px; background-color:#1c1c1c; color:#fff; font-size:14px; font-weight:bold; border-left:4px solid #0088cc;'>{decision}</div>", unsafe_allow_html=True)

            log_html = ""
            if st.session_state.order_history:
                for item in st.session_state.order_history[:5]:
                    color = "#ff4466" if item['side'] == 'Buy' else "#00ff88"
                    action = "外盤買進" if item['side'] == 'Buy' else "內盤賣出"
                    log_html += f"<div style='color:{color}; font-size:13px; padding: 2px 0;'>{item['time_str']} | {item['price']:.2f} | {item['qty']}張 ({action})</div>"
            else:
                log_html = "<div style='color:#888; font-size:13px;'>等待大戶進場中...</div>"
            log_spot.markdown(log_html, unsafe_allow_html=True)

        except FugleAPIError as e:
            st.error("🚨 API 異常，冷卻中...")
            time.sleep(2)
        except Exception as e:
            st.error(f"系統錯誤: {e}")
            
        time.sleep(2)

# 啟動主流程
start_streaming(stock_code)
