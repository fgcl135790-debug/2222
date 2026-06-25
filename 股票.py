import streamlit as st
import pandas as pd
import datetime
import time

# ==========================================
# 1. 頁面基本設定 (請放在程式碼最上方)
# ==========================================
st.set_page_config(page_title="股票監控儀表板", layout="wide")

# ==========================================
# 2. 側邊欄設定：輸入金鑰與參數
# ==========================================
with st.sidebar:
    st.header("⚙️ 設定：輸入金鑰 / 更換股票")
    
    # 隱藏密碼輸入
    api_key = st.text_input("富果 API Key", type="password")
    stock_id = st.text_input("股票代號", value="2409")
    
    col1, col2 = st.columns(2)
    with col1:
        large_order_def = st.number_input("🔥 大戶定義 (張)", value=5, step=1)
    with col2:
        ref_volume_ratio = st.number_input("📊 參考量比 (倍)", value=1.2, step=0.1)
        
    night_mode = st.checkbox("🌙 啟動深夜模擬測試 (半夜看畫面專用)")

# ==========================================
# 3. 頂部狀態提示區 (取代 st.toast，避免擋住右下角)
# ==========================================
# 檢查 API Key
if not api_key:
    st.warning("🔑 請先展開左側選單輸入「富果 API Key」以啟動功能。")
    st.stop()  # 停止渲染下方畫面直到輸入 Key

# 多空交戰提示 (你可以依據程式邏輯用 st.empty() 或條件判斷來動態改變這行)
st.info("⚖️ 目前多空交戰或無大單進出，建議觀望")

# ==========================================
# 4. 富果 API 串接區 (請替換為你的真實資料邏輯)
# ==========================================
# 下方為模擬的變數，請對接你的 WebSocket 或 REST API 取回的值
stock_name = f"友達 ({stock_id})"
stock_price = 30.40
market_status = "大盤震盪"
vwap = 30135.22
current_time = datetime.datetime.now().strftime("%H:%M:%S")

# ==========================================
# 5. 放大顯示區：目前股價、大盤、均價線
# ==========================================
st.markdown(
    f"""
    <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 32px; font-weight: bold; color: white;">📈 {stock_name}</span>
            <span style="font-size: 36px; font-weight: bold; color: #00FF00;">{stock_price:.2f}</span>
        </div>
        <div style="font-size: 20px; color: #CCCCCC; border-top: 1px solid #444; padding-top: 15px;">
            大盤: ⚪ {market_status} &nbsp;&nbsp;|&nbsp;&nbsp; 均價線 (VWAP): {vwap:.2f} &nbsp;&nbsp;|&nbsp;&nbsp; 時間: {current_time}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ==========================================
# 6. 盤口最佳五檔
# ==========================================
st.markdown("### 📋 盤口最佳五檔")

# 這裡填寫你的五檔資料 (替換成從 API 取得的 dict)
data_5_bids_asks = {
    "買張": [173, 1305, 1119, 1627, 1419],
    "買價": [30.40, 30.35, 30.30, 30.25, 30.20],
    "賣價": [30.45, 30.50, 30.55, 30.60, 30.65],
    "賣張": [1068, 2612, 803, 2720, 554]
}
df_5_bids_asks = pd.DataFrame(data_5_bids_asks)

# 設定 DataFrame 的字體顏色：買方綠色 (#00FF00)，賣方紅色 (#FF4B4B)
def color_bids_asks(val, color):
    return f'color: {color}; font-weight: bold;'

styled_df = df_5_bids_asks.style\
    .map(lambda x: color_bids_asks(x, '#00FF00'), subset=['買張', '買價'])\
    .map(lambda x: color_bids_asks(x, '#FF4B4B'), subset=['賣價', '賣張'])

# 顯示表格並隱藏左側 Index
st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ==========================================
# 7. 多空動能燈號 & 大戶進攻紀錄
# ==========================================
st.markdown("---")

st.markdown("### 🔥 多空動能燈號")
# 請將你判斷多空的邏輯輸出在這裡
st.write("目前多空交戰或無大單進出，建議觀望") 

st.markdown("### 📜 大戶進攻即時紀錄")
# 請將大戶明細的 DataFrame 輸出在這裡
st.write("等待大戶進場中...")

# 如果你原本有寫 time.sleep 或 st.rerun() 來做畫面更新，可以加在最下方
# time.sleep(1)
# st.rerun()
