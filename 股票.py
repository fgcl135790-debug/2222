import streamlit as st
import time
from fugle_marketdata import RestClient, FugleAPIError

# --- 1. 配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", layout="centered")
st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 2. 設定選單 (保持你原有的配置) ---
with st.expander("⚙️ 設定選單", expanded=True):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    app_mode = st.radio("運作模式", ["☀️ 即時串流", "🌙 模擬測試", "⏳ 真實歷史回放"], index=2)
    app_speed = st.slider("回放加速度", 1, 50, 25)
    pause = st.toggle("⏸️ 暫停回放")

# --- 3. 核心大戶判定引擎 (修正版) ---
def get_decision(recent_buy, recent_sell, price, open_price):
    # 當「倒貨」次數大於「點火」次數，強制進入空頭邏輯
    if recent_sell > recent_buy and recent_sell >= 3:
        return "做空", "🎯【💥 強制做空】主力大量倒貨中！"
    elif recent_buy >= 3:
        return "做多", "🎯【🔥 積極做多】主力連環點火！"
    return "觀望", "⏳ 偵測中：多空拉鋸..."

# --- 4. 狀態初始化 ---
if 'history' not in st.session_state: st.session_state.history = []
if 'idx' not in st.session_state: st.session_state.idx = 0

# --- 5. 主執行迴圈 ---
@st.fragment(run_every=1.0)
def main():
    # 模擬數據生成 (保持原汁原味)
    idx = st.session_state.idx
    if not pause: st.session_state.idx += app_speed
    
    price = 31.50 - (idx * 0.001)
    qty = random.randint(100, 900) * 1000
    
    # 紀錄大單
    if qty >= 400000: # 大戶門檻設 400 張
        st.session_state.history.append({'side': 'Buy' if price > 31 else 'Sell', 'qty': qty})
        
    # 計算訊號
    buys = sum(1 for h in st.session_state.history[-10:] if h['side'] == 'Buy')
    sells = sum(1 for h in st.session_state.history[-10:] if h['side'] == 'Sell')
    
    decision, msg = get_decision(buys, sells, price, 31.10)
    
    # UI 呈現
    st.header(f"📈 {price:.2f} 元")
    if decision == "做多": st.success(msg)
    elif decision == "做空": st.error(msg)
    else: st.info(msg)
    
    # 顯示流水帳
    for h in reversed(st.session_state.history[-5:]):
        st.write(f"{h['side']} {h['qty']:,}張")

main()
