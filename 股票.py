import streamlit as st
import time
import random 
from fugle_marketdata import RestClient, FugleAPIError

st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="centered")
st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 設定選單 ---
with st.expander("⚙️ 設定選單", expanded=True):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    app_mode = st.radio("運作模式", ["☀️ 即時串流", "🌙 隨機模擬", "⏳ 真實回放 (覆盤)"], index=0)
    app_speed = st.slider("⏩ 回放加速度 (倍速)", 1, 50, 25)
    pause_toggle = st.toggle("⏸️ 暫停歷史回放", value=False)
    if app_mode == "⏳ 真實回放 (覆盤)":
        if st.button("🔄 重置覆盤"):
            st.session_state.replay_index = 0
            st.session_state.order_history = []
            st.rerun()

# --- 初始化狀態 ---
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'replay_trades' not in st.session_state: st.session_state.replay_trades = []
if 'replay_index' not in st.session_state: st.session_state.replay_index = 0

# --- 核心邏輯引擎 ---
def get_threshold(price, vol):
    return 500 if price < 50 else 200 # 友達門檻固定

# --- 容器 ---
index_container = st.container()
price_container = st.container()
signal_container = st.container()
five_ticks_container = st.container()
fire_container = st.container()

# --- 資料更新循環 ---
@st.fragment(run_every=2.0)
def streaming():
    try:
        client = RestClient(api_key=api_key) if api_key else None
        
        # 1. 取得價格數據 (模擬或真實)
        if app_mode == "⏳ 真實回放 (覆盤)":
            if not st.session_state.replay_trades:
                # 載入 2000 筆模擬劇本
                st.session_state.replay_trades = [{'price': 31.10 + (i*0.005), 'size': (550000 if i%10==0 else 2000), 'time': 1719190800 + i} for i in range(2000)]
            
            if not pause_toggle:
                batch = st.session_state.replay_trades[st.session_state.replay_index : st.session_state.replay_index + app_speed]
                st.session_state.replay_index += len(batch)
                
            tick = st.session_state.replay_trades[min(st.session_state.replay_index, len(st.session_state.replay_trades)-1)]
            price = tick['price']
            qty = tick['size']
            prog = st.session_state.replay_index / 2000
        else:
            # 即時模式 (簡化版)
            price, qty = 31.50, 1000
            prog = 0.5

        # 2. 強制連動運算 (無論暫停與否都要算)
        taiex = 22135 - (prog * 150)
        otc = 265 - (prog * 10)
        
        # 五檔呼吸 (根據價格隨機)
        random.seed(int(price * 100))
        bids = [{'price': round(price - 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]
        asks = [{'price': round(price + 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]
        
        # 3. 渲染畫面
        with index_container:
            st.write(f"大盤: {taiex:.2f} | 櫃買: {otc:.2f}")
        
        with price_container:
            st.header(f"📈 友達 ({stock_code}) : {price:.2f} 元")
            
        with five_ticks_container:
            st.table([{'買張': f"{b['size']:,}", '買價': b['price'], '賣價': a['price'], '賣張': f"{a['size']:,}"} 
                      for b, a in zip(bids, asks)])
            
        # 4. 火網判定 (修復：必須把數據傳入邏輯)
        if qty >= 500000:
            st.session_state.order_history.append({'time': time.strftime("%H:%M:%S"), 'qty': qty, 'price': price, 'side': 'Buy' if price > 31 else 'Sell'})
            
        with fire_container:
            st.write(f"火網紀錄: {len(st.session_state.order_history)} 筆")
            for h in reversed(st.session_state.order_history[-5:]):
                st.write(f"{h['time']} | {h['side']} {h['qty']:,}張 @ {h['price']}")

    except Exception as e:
        st.error(f"連線異常: {e}")

streaming()
