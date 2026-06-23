import streamlit as st
import time
import random 
from fugle_marketdata import RestClient, FugleAPIError

# --- 配置 ---
st.set_page_config(page_title="行動大戶籌碼監控", page_icon="⚡", layout="centered")
st.title("⚡ 行動大戶籌碼五檔 APP")

# --- 渲染組件 ---
def render_index(taiex_price, taiex_change, otc_price, otc_change):
    tx_color = "#ff4466" if taiex_change >= 0 else "#00ff88"
    otc_color = "#ff4466" if otc_change >= 0 else "#00ff88"
    html = f"""
    <table style='width:100%; text-align:center; font-size:13px; margin-bottom:10px;'>
        <tr>
            <td style='width:49%; background-color:#161b22; padding:8px; border-radius:6px;'>
                <span style='color:#888; font-size:11px;'>加權大盤</span><br>
                <b style='color:{tx_color}; font-size:16px;'>{taiex_price:,.2f}</b> 
                <span style='color:{tx_color}; font-size:11px;'>({taiex_change:+.2f})</span>
            </td>
            <td style='width:2%;'></td>
            <td style='width:49%; background-color:#161b22; padding:8px; border-radius:6px;'>
                <span style='color:#888; font-size:11px;'>櫃買指數</span><br>
                <b style='color:{otc_color}; font-size:16px;'>{otc_price:,.2f}</b> 
                <span style='color:{otc_color}; font-size:11px;'>({otc_change:+.2f})</span>
            </td>
        </tr>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_five_ticks(bids, asks):
    html = "<table style='width:100%; text-align:center; font-size:15px; border-collapse:collapse; font-family:monospace;'>"
    html += "<tr style='background-color:#111; height:30px;'><th style='color:#00ff88; width:25%;'>買張</th><th style='color:#00ff88; width:25%;'>買價</th><th style='color:#ff4466; width:25%;'>賣價</th><th style='color:#ff4466; width:25%;'>賣張</th></tr>"
    for i in range(5):
        html += f"<tr style='height:35px; border-bottom:1px solid #222;'>"
        html += f"<td style='color:#00ff88;'>{int(bids[i]['size']/1000):,}</td><td style='color:#00ff88; font-weight:bold;'>{bids[i]['price']}</td>"
        html += f"<td style='color:#ff4466; font-weight:bold;'>{asks[i]['price']}</td><td style='color:#ff4466;'>{int(asks[i]['size']/1000):,}</td>"
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

# --- 設定選單 ---
with st.expander("⚙️ 展開設定 / 50倍速控制", expanded=True):
    api_key = st.text_input("富果 API Key", type="password")
    stock_code = st.text_input("股票代號", value="2409")
    app_mode = st.radio("模式", ["☀️ 即時", "🌙 模擬", "⏳ 回放"], index=2)
    app_speed = st.slider("⏩ 倍速", 1, 50, 25)
    pause_toggle = st.toggle("⏸️ 暫停回放", value=False)
    if st.button("🔄 重置"):
        st.session_state.replay_index = 0
        st.session_state.order_history = []
        st.rerun()

# --- 初始化狀態 ---
if 'order_history' not in st.session_state: st.session_state.order_history = []
if 'replay_index' not in st.session_state: st.session_state.replay_index = 0
if 'replay_trades' not in st.session_state: st.session_state.replay_trades = []

# --- 主程式 ---
@st.fragment(run_every=2.0)
def streaming():
    try:
        # 1. 回放資料準備
        if app_mode == "⏳ 真實回放":
            if not st.session_state.replay_trades:
                st.session_state.replay_trades = [{'price': round(31.10 + (i*0.005), 2), 'size': random.randint(100, 900)*1000, 'time': 1719190800 + i*2} for i in range(2000)]
            if not pause_toggle:
                st.session_state.replay_index = min(st.session_state.replay_index + app_speed, 1999)
            idx = st.session_state.replay_index
            tick = st.session_state.replay_trades[idx]
            price, qty = tick['price'], tick['size']
            prog = idx / 2000
        else:
            price, qty = 31.50, 1000
            prog = 0.5
            
        # 2. 數據運算
        taiex = 22135 - (prog * 150)
        taiex_change = -150.32 * prog
        otc = 265 - (prog * 10)
        otc_change = 1.45 * prog
        
        bids = [{'price': round(price - 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]
        asks = [{'price': round(price + 0.05*(i+1), 2), 'size': random.randint(1000, 9000)*1000} for i in range(5)]
        total_bid = sum(b['size'] for b in bids)
        total_ask = sum(a['size'] for a in asks)
        
        # 3. 畫面渲染 (精緻排版回歸)
        render_index(taiex, taiex_change, otc, otc_change)
        st.header(f"📈 友達 ({stock_code}) : {price:.2f} 元")
        
        render_five_ticks(bids, asks)
        
        # 4. 火網判定
        if qty >= 500000:
            st.session_state.order_history.append({'time': time.strftime("%H:%M:%S"), 'qty': qty, 'price': price, 'side': 'Buy' if price > 31 else 'Sell'})
            
        st.subheader("🔥 30秒大戶火網")
        for h in reversed(st.session_state.order_history[-5:]):
            st.write(f"⏱️ {h['time']} | {'外盤吃貨' if h['side']=='Buy' else '內盤倒貨'} {h['qty']:,}張 @ {h['price']}")
                
    except Exception as e:
        st.error(f"運行異常: {e}")

streaming()
