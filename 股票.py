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
    app_mode = st.radio("運作模式", ["☀️ 即時串流", "🌙 隨機模擬", "⏳ 真實歷史回放"], index=2)
    app_speed = st.slider("⏩ 回放加速度", 1, 50, 25)
    pause_toggle = st.toggle("⏸️ 暫停歷史回放", value=False)
    if st.button("🔄 重置覆盤"):
        st.session_state.replay_index = 0
        st.session_state.order_history = []
        st.rerun()

# --- 初始化狀態 ---
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'replay_index' not in st.session_state: st.session_state.replay_index = 0
if 'replay_trades' not in st.session_state: st.session_state.replay_trades = []

# --- 核心邏輯 ---
@st.fragment(run_every=2.0)
def streaming():
    try:
        # 覆盤資料準備
        if app_mode == "⏳ 真實歷史回放" and not st.session_state.replay_trades:
            st.session_state.replay_trades = [{'price': 31.10 + (i*0.005), 'size': random.randint(100, 900)*1000, 'time': 1719190800 + i*2} for i in range(2000)]
        
        # 指標連動
        idx = st.session_state.replay_index
        prog = idx / 2000 if app_mode == "⏳ 真實歷史回放" else 0.5
        taiex = 22135 - (prog * 150)
        otc = 265 - (prog * 10)
        
        # 讀取當前價格
        if app_mode == "⏳ 真實歷史回放":
            if not pause_toggle: st.session_state.replay_index = min(idx + app_speed, 1999)
            tick = st.session_state.replay_trades[st.session_state.replay_index]
            price, qty = tick['price'], tick['size']
        else:
            price, qty = 31.50, 1000

        # 五檔
        random.seed(int(price * 100))
        bids = [{'price': round(price - 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]
        asks = [{'price': round(price + 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]

        # 渲染
        st.write(f"大盤: {taiex:.2f} | 櫃買: {otc:.2f}")
        st.header(f"📈 友達 ({stock_code}) : {price:.2f} 元")
        
        st.table([{'買張': f"{b['size']:,}", '買價': b['price'], '賣價': a['price'], '賣張': f"{a['size']:,}"} 
                  for b, a in zip(bids, asks)])
        
        # 火網判斷 (補齊 append 邏輯)
        if qty >= 500000:
            st.session_state.order_history.append({
                'time': time.strftime("%H:%M:%S"), 
                'qty': qty, 
                'price': price, 
                'side': 'Buy' if price > 31 else 'Sell'
            })
            
        st.write(f"大單紀錄: {len(st.session_state.order_history)} 筆")
        for h in reversed(st.session_state.order_history[-5:]):
            st.write(f"{h['time']} | {h['side']} {h['qty']:,}張 @ {h['price']}")
                
    except Exception as e:
        st.error(f"程式運行異常: {e}")

streaming()
