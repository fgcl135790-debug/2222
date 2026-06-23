import streamlit as st
import time
import random
from fugle_marketdata import RestClient, FugleAPIError

# --- 設定 ---
st.set_page_config(layout="centered", page_title="大戶籌碼監控")
st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 設定欄 ---
with st.expander("⚙️ 點我展開：設定 / 倍速控制", expanded=True):
    api_key = st.text_input("API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    mode = st.radio("模式", ["即時", "回放"], index=1)
    speed = st.slider("回放倍速", 1, 50, 25)
    if st.button("🔄 重置"):
        st.session_state.idx = 0
        st.session_state.history = []
        st.rerun()

# --- 初始化狀態 ---
if 'history' not in st.session_state: st.session_state.history = []
if 'idx' not in st.session_state: st.session_state.idx = 0

# --- 模擬數據產生器 ---
def get_data(idx):
    price = 31.50 - (idx * 0.001)
    qty = random.randint(100, 900) * 1000
    return round(price, 2), qty

# --- 主程式 ---
idx = st.session_state.idx
price, qty = get_data(idx)
st.session_state.idx += speed

# 五檔數據產生
bids = [{'價': round(price - 0.05*i, 2), '量': f"{random.randint(1000, 9000):,}"} for i in range(1, 6)]
asks = [{'價': round(price + 0.05*i, 2), '量': f"{random.randint(1000, 9000):,}"} for i in range(1, 6)]

# UI 佈局
st.metric("當前股價", f"{price:.2f}", delta="-0.10")
col1, col2 = st.columns(2)
with col1:
    st.table(bids)
with col2:
    st.table(asks)

# 大單監控
if qty >= 500000:
    st.session_state.history.append({'time': time.strftime("%H:%M:%S"), 'qty': qty, 'price': price, 'side': '外盤' if price > 31 else '內盤'})

st.subheader("🔥 30秒大戶進攻火網")
hist = st.session_state.history[-5:]
for h in reversed(hist):
    st.write(f"⏱️ {h['time']} | {h['side']} {h['qty']:,}張 @ {h['price']}")

time.sleep(1)
st.rerun()
