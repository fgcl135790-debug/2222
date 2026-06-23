import streamlit as st
import time
import random
from fugle_marketdata import RestClient, FugleAPIError

# --- 設定 ---
st.set_page_config(page_title="行動大戶籌碼監控", layout="centered")
st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 側邊與設定 ---
with st.expander("⚙️ 設定選單", expanded=True):
    api_key = st.text_input("API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    mode = st.radio("模式", ["即時", "回放"], index=1)
    speed = st.slider("倍速", 1, 50, 25)
    pause = st.toggle("⏸️ 暫停回放")
    if st.button("🔄 重置"):
        st.session_state.idx = 0
        st.session_state.history = []
        st.rerun()

# --- 初始化 ---
if 'history' not in st.session_state: st.session_state.history = []
if 'idx' not in st.session_state: st.session_state.idx = 0
if 'trades' not in st.session_state: st.session_state.trades = [{'price': round(31.50 - (i*0.005), 2), 'size': random.randint(100, 900)*1000} for i in range(2000)]

# --- 核心邏輯 ---
def main_engine():
    idx = st.session_state.idx
    if mode == "回放" and not pause:
        idx = min(idx + speed, 1999)
        st.session_state.idx = idx
        
    tick = st.session_state.trades[idx] if mode == "回放" else {'price': 31.50, 'size': 600000}
    price, qty = tick['price'], tick['size']
    
    # 顯示區塊
    st.header(f"📈 友達: {price:.2f} 元")
    
    # 五檔渲染 (CSS 優化)
    bids = [{'價': round(price - 0.05*i, 2), '張': random.randint(1000, 9000)*1000} for i in range(1, 6)]
    asks = [{'價': round(price + 0.05*i, 2), '張': random.randint(1000, 9000)*1000} for i in range(1, 6)]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("買入五檔")
        st.table([{'買價': b['價'], '買張': f"{b['張']:,}"} for b in bids])
    with col2:
        st.subheader("賣出五檔")
        st.table([{'賣價': a['價'], '賣張': f"{a['張']:,}"} for a in asks])
        
    # 大戶紀錄
    if qty >= 500000:
        st.session_state.history.append({'time': time.strftime("%H:%M:%S"), 'qty': qty, 'price': price, 'side': '外盤' if price > 31 else '內盤'})
    
    st.subheader("🔥 30秒大戶進攻火網")
    hist = st.session_state.history[-5:]
    for h in reversed(hist):
        color = "#ff4b4b" if h['side'] == '外盤' else "#00cc96"
        st.markdown(f"⏱️ {h['time']} | <b style='color:{color}'>{h['side']} {h['qty']:,}張 @ {h['price']}</b>", unsafe_allow_html=True)

# 執行
main_engine()
time.sleep(1)
st.rerun()
