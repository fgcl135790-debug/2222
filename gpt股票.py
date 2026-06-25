import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from fugle_marketdata import RestClient
from datetime import datetime

st.set_page_config(page_title="REST PRO 大戶監控", page_icon="⚡", layout="wide")

st_autorefresh(interval=2000, key="refresh")

for key, default in {
    "price_history": [],
    "last_bid_vol": 0,
    "last_ask_vol": 0,
    "big_order_log": [],
    "last_trade_serial": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.header("⚙️ 系統設定")
    api_key = st.text_input("Fugle API Key", type="password")
    stock_code = st.text_input("股票代號", value="2330")
    big_order_size = st.number_input("大戶定義(張)", min_value=1, value=100)

if not api_key:
    st.warning("請輸入 Fugle API Key")
    st.stop()

try:
    client = RestClient(api_key=api_key)
    quote = client.stock.intraday.quote(symbol=stock_code)
except Exception as e:
    st.error(f"取得資料失敗: {e}")
    st.stop()

stock_name = quote.get("name", stock_code)
current_price = quote.get("lastPrice", 0)
open_price = quote.get("openPrice", current_price)
high_price = quote.get("highPrice", current_price)
low_price = quote.get("lowPrice", current_price)
vwap = quote.get("avgPrice", current_price)
last_size = quote.get("lastSize", 0)

bids = quote.get("bids", [])
asks = quote.get("asks", [])
is_close = quote.get("isClose", False)

st.session_state["price_history"].append(current_price)
st.session_state["price_history"] = st.session_state["price_history"][-300:]

series = pd.Series(st.session_state["price_history"])
ema5 = series.ewm(span=5).mean().iloc[-1] if len(series) >= 5 else current_price
ema20 = series.ewm(span=20).mean().iloc[-1] if len(series) >= 20 else current_price

signal = "盤整"
if current_price > vwap and ema5 > ema20:
    signal = "多頭"
elif current_price < vwap and ema5 < ema20:
    signal = "空頭"

st.title(f"{stock_name} ({stock_code})")
c1, c2, c3, c4 = st.columns(4)
c1.metric("現價", current_price)
c2.metric("VWAP", round(vwap, 2))
c3.metric("EMA5", round(float(ema5), 2))
c4.metric("EMA20", round(float(ema20), 2))

c1, c2, c3, c4 = st.columns(4)
c1.metric("高點", high_price)
c2.metric("低點", low_price)
c3.metric("最新成交量", last_size)
c4.metric("趨勢", signal)

if is_close:
    st.warning("目前已收盤")

while len(bids) < 5:
    bids.append({"price": 0, "size": 0})
while len(asks) < 5:
    asks.append({"price": 0, "size": 0})

df = pd.DataFrame({
    "買張": [x.get("size", 0) for x in bids[:5]],
    "買價": [x.get("price", 0) for x in bids[:5]],
    "賣價": [x.get("price", 0) for x in asks[:5]],
    "賣張": [x.get("size", 0) for x in asks[:5]],
})
st.subheader("📋 最佳五檔")
st.dataframe(df, use_container_width=True, hide_index=True)

total_bid = sum(x.get("size", 0) for x in bids)
total_ask = sum(x.get("size", 0) for x in asks)
order_ratio = total_bid / total_ask if total_ask else 0
vwap_dev = ((current_price - vwap) / vwap * 100) if vwap else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("委買總量", total_bid)
c2.metric("委賣總量", total_ask)
c3.metric("委買賣比", f"{order_ratio:.2f}")
c4.metric("VWAP偏離", f"{vwap_dev:.2f}%")

wall_threshold = 1000
buy_walls = [x for x in bids if x.get("size", 0) >= wall_threshold]
sell_walls = [x for x in asks if x.get("size", 0) >= wall_threshold]

if buy_walls:
    st.success(f"🟢 巨量買牆 {buy_walls[0]['price']} ({buy_walls[0]['size']}張)")
if sell_walls:
    st.error(f"🔴 巨量賣牆 {sell_walls[0]['price']} ({sell_walls[0]['size']}張)")

if st.session_state["last_bid_vol"] > 0:
    diff = st.session_state["last_bid_vol"] - total_bid
    if diff > 500 and diff / st.session_state["last_bid_vol"] > 0.2:
        st.warning("🚨 買盤大量撤單")

if st.session_state["last_ask_vol"] > 0:
    diff = st.session_state["last_ask_vol"] - total_ask
    if diff > 500 and diff / st.session_state["last_ask_vol"] > 0.2:
        st.info("🚨 賣盤大量撤單")

st.session_state["last_bid_vol"] = total_bid
st.session_state["last_ask_vol"] = total_ask

trade = quote.get("lastTrade", {})
trade_serial = trade.get("serial")
trade_price = trade.get("price", current_price)
trade_size = trade.get("size", 0)

if trade_serial and trade_serial != st.session_state["last_trade_serial"]:
    st.session_state["last_trade_serial"] = trade_serial

    if trade_size >= big_order_size:
        bid_price = trade.get("bid", 0)
        ask_price = trade.get("ask", 0)

        if trade_price >= ask_price:
            side = "Buy"
        elif trade_price <= bid_price:
            side = "Sell"
        else:
            side = "Unknown"

        st.session_state["big_order_log"].insert(0, {
            "時間": datetime.now().strftime("%H:%M:%S"),
            "價格": trade_price,
            "張數": trade_size,
            "方向": side
        })

st.subheader("📜 大戶成交紀錄")
if st.session_state["big_order_log"]:
    st.dataframe(pd.DataFrame(st.session_state["big_order_log"][:20]), use_container_width=True, hide_index=True)
else:
    st.info("尚未偵測到大戶成交")

st.caption(f"最後更新：{datetime.now().strftime('%H:%M:%S')}")
