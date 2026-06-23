import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="當沖不閃爍監控", page_icon="📈", layout="centered")

st.title("📈 全自動當沖監控 (無閃爍優化版)")
st.write("利用局部定時洗價技術，保持畫面完全靜止，僅數據即時跳動。")

stock_code = st.text_input("輸入要監控的股票代號", value="2409")

# 在全域初始化開盤價，避免局部刷新時資料遺失
if 'open_price' not in st.session_state:
    st.session_state.open_price = 0.0

def fetch_yahoo_stock(code):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{code}.TW"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.find('span', {'class': 'Fz(32px)'}) 
        return float(price_element.text) if price_element else None
    except:
        return None

# --- 🎯 核心特技：利用 st.fragment 建立「局部刷新區」 ---
@st.fragment(run_every=1.0) 
def monitor_panel(code):
    current_p = fetch_yahoo_stock(code)
    
    if current_p:
        if st.session_state.open_price == 0.0:
            st.session_state.open_price = current_p
            
        # 🕒 1. 自動抓取當下電腦/手機的最新秒級時間
        current_time = time.strftime("%H:%M:%S")
            
        # 📐 2. 建立並排欄位（左邊佔 3 等分放股價，右邊佔 1 等分放時間）
        col_price, col_time = st.columns([3, 1])
        
        with col_price:
            # 左邊欄位：原本的即時股價
            st.metric(
                label=f"📊 友達 ({code}) 即時股價", 
                value=f"{current_p} 元", 
                delta=f"相較今日開盤: {round(current_p - st.session_state.open_price, 2)} 元"
            )
            
        with col_time:
            # 右邊欄位：放你想要的最後更新時間
            st.metric(
                label="⏱️ 最後更新時間",
                value=current_time
            )
        
        # 即時判定輸出
        if current_p < st.session_state.open_price:
            st.error("🚨 【假希望/偏弱】股價跌破開盤價！當沖多單請注意防守。")
        else:
            st.success("🔥 【真希望/偏強】股價立足於開盤價之上，多方嘗試控盤中！")
    else:
        st.warning("⏳ 正在背景即時抓取數據中...")
