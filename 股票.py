import streamlit as st
import time
import random
from fugle_marketdata import RestClient, FugleAPIError

# --- 手機版原生視窗最佳化配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="centered")

st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 設定選單 ---
with st.expander("⚙️ 點我展開：設定 / 倍速 / 暫停", expanded=True):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    app_mode = st.radio("運作模式", ["☀️ 即時串流", "🌙 隨機模擬", "⏳ 真實歷史回放"], index=0)
    app_speed = st.slider("⏩ 回放加速度 (倍速)", 1, 50, 25)
    pause_toggle = st.toggle("⏸️ 暫停歷史回放", value=False)
    if st.button("🔄 重置覆盤"):
        st.session_state.replay_index = 0
        st.session_state.order_history = []
        st.rerun()

# --- 矩陣定義 ---
def get_threshold(price, vol):
    return 500 if price < 50 else 200

# --- 初始化 ---
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'replay_trades' not in st.session_state: st.session_state.replay_trades = []
if 'replay_index' not in st.session_state: st.session_state.replay_index = 0
if 'last_update_time' not in st.session_state: st.session_state.last_update_time = time.time()

# --- 核心顯示區塊 ---
index_block = st.empty()
price_block = st.empty()
fire_block = st.empty()
five_ticks_block = st.empty()

@st.fragment(run_every=2.0)
def streaming():
    try:
        # --- 數據引擎 ---
        if app_mode == "⏳ 真實歷史回放":
            if not st.session_state.replay_trades:
                # 載入 2000 筆劇本
                st.session_state.replay_trades = [{'price': 31.10 + (i*0.005), 'size': (500000 if i%20==0 else 2000), 'time': 1719190800 + i*2} for i in range(2000)]
            
            if not pause_toggle:
                st.session_state.replay_index = min(st.session_state.replay_index + app_speed, 1999)
            
            tick = st.session_state.replay_trades[st.session_state.replay_index]
            price, qty = tick['price'], tick['size']
            prog = st.session_state.replay_index / 2000
        else:
            price, qty = 31.50, 1000 # 模擬即時
            prog = 0.5
            
        # --- 計算連動數據 ---
        taiex = 22135 - (prog * 150)
        otc = 265 - (prog * 10)
        random.seed(int(price * 100))
        bids = [{'price': round(price - 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]
        asks = [{'price': round(price + 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]

        # --- 渲染 ---
        index_block.write(f"加權: {taiex:.2f} | 櫃買: {otc:.2f}")
        price_block.header(f"📈 友達 ({stock_code}) : {price:.2f} 元")
        
        with five_ticks_block:
            st.table([{'買張': f"{b['size']:,}", '買價': b['price'], '賣價': a['price'], '賣張': f"{a['size']:,}"} 
                      for b, a in zip(bids, asks)])
            
        if qty >= 500000:
            st.session_state.order_history.append({'time': time.strftime("%H:%M:%S"), 'qty': qty, 'price': price, 'side': 'Buy' if price > 31 else 'Sell'})
            
        with fire_block:
            st.write(f"大單紀錄: {len(st.session_state.order_history)} 筆")
            for h in reversed(st.session_state.order_history[-5:]):
                st.write(f"{h['time']} | {h['side']} {h['qty']:,}張 @ {h['price']}")
                
    except Exception as e:
        st.error(f"程式運行異常: {e}")

streaming()
