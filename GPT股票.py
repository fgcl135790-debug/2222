import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from fugle_marketdata import RestClient

# =========================

# Page Config

# =========================

st.set_page_config(
page_title="專業版大戶監控",
page_icon="⚡",
layout="wide"
)

st.markdown("""

<style>
.block-container{
    padding-top:0.5rem;
    max-width:100%;
}

.price-card{
    background:#1f1f1f;
    border-radius:12px;
    padding:18px;
    border:1px solid #333;
}

.signal-long{
    background:#0d3b1f;
    color:#00ff88;
    padding:12px;
    border-radius:8px;
    font-weight:bold;
}

.signal-short{
    background:#3d1111;
    color:#ff6666;
    padding:12px;
    border-radius:8px;
    font-weight:bold;
}

.signal-neutral{
    background:#252525;
    color:white;
    padding:12px;
    border-radius:8px;
    font-weight:bold;
}
</style>

""", unsafe_allow_html=True)

# =========================

# Auto Refresh

# =========================

st_autorefresh(interval=2000, key="refresh")

# =========================

# Session State

# =========================

if "price_history" not in st.session_state:
    st.session_state["price_history"] = []

if "last_bid_vol" not in st.session_state:
    st.session_state["last_bid_vol"] = 0

if "last_ask_vol" not in st.session_state:
    st.session_state["last_ask_vol"] = 0

if "big_order_log" not in st.session_state:
    st.session_state["big_order_log"] = []

# =========================

# Sidebar

# =========================

with st.sidebar:

```
st.header("⚙️ 系統設定")

api_key = st.text_input(
    "Fugle API Key",
    type="password"
)

stock_code = st.text_input(
    "股票代號",
    value="2330"
)

big_order_size = st.number_input(
    "大戶定義(張)",
    min_value=1,
    value=100
)
```

if not api_key:
st.warning("請輸入 Fugle API Key")
st.stop()

# =========================

# Load Data

# =========================

try:

```
client = RestClient(api_key=api_key)

quote = client.stock.intraday.quote(
    symbol=stock_code
)
```

except Exception as e:

```
st.error(f"取得資料失敗: {e}")
st.stop()
```

# =========================

# Parse Data

# =========================

stock_name = quote.get("name", stock_code)

current_price = (
quote.get("lastPrice")
or quote.get("lastTrade", {}).get("price")
or 0
)

open_price = quote.get("openPrice", current_price)

high_price = quote.get("highPrice", current_price)

low_price = quote.get("lowPrice", current_price)

vwap = quote.get("avgPrice", current_price)

last_size = (
quote.get("lastSize")
or quote.get("lastTrade", {}).get("size")
or 0
)

bids = quote.get("bids", [])
asks = quote.get("asks", [])

is_close = quote.get("isClose", False)

# =========================

# EMA

# =========================

st.session_state.price_history.append(current_price)

if len(st.session_state.price_history) > 200:
st.session_state.price_history.pop(0)

price_series = pd.Series(
st.session_state.price_history
)

ema5 = (
price_series.ewm(span=5).mean().iloc[-1]
if len(price_series) >= 5
else current_price
)

ema20 = (
price_series.ewm(span=20).mean().iloc[-1]
if len(price_series) >= 20
else current_price
)

# =========================

# Trend Signal

# =========================

signal = "盤整"

if current_price > vwap and ema5 > ema20:
signal = "多頭"

elif current_price < vwap and ema5 < ema20:
signal = "空頭"

# =========================

# Header

# =========================

change = current_price - open_price

color = "#ff4466" if change >= 0 else "#00ff88"

st.markdown(f"""

<div class="price-card">
<h2>{stock_name} ({stock_code})</h2>

<div style="
font-size:42px;
font-weight:bold;
color:{color};
">
{current_price}
</div>

<div>
VWAP：{vwap:.2f}
<br>
EMA5：{ema5:.2f}
<br>
EMA20：{ema20:.2f}
<br>
今日高點：{high_price}
<br>
今日低點：{low_price}
</div>
</div>
""", unsafe_allow_html=True)

# =========================

# Signal

# =========================

if signal == "多頭":

```
st.markdown(
    '<div class="signal-long">🔥 多頭趨勢</div>',
    unsafe_allow_html=True
)
```

elif signal == "空頭":

```
st.markdown(
    '<div class="signal-short">🧊 空頭趨勢</div>',
    unsafe_allow_html=True
)
```

else:

```
st.markdown(
    '<div class="signal-neutral">⚖️ 盤整</div>',
    unsafe_allow_html=True
)
```

# =========================

# 收盤保護

# =========================

if is_close:
st.warning("目前已收盤")

# =========================

# 五檔

# =========================

while len(bids) < 5:
bids.append({"price":0,"size":0})

while len(asks) < 5:
asks.append({"price":0,"size":0})

df = pd.DataFrame({
"買張":[x["size"] for x in bids[:5]],
"買價":[x["price"] for x in bids[:5]],
"賣價":[x["price"] for x in asks[:5]],
"賣張":[x["size"] for x in asks[:5]]
})

st.subheader("📋 最佳五檔")

st.dataframe(
df,
use_container_width=True,
hide_index=True
)

# =========================

# 撤單偵測

# =========================

total_bid = sum(x["size"] for x in bids)
total_ask = sum(x["size"] for x in asks)

if st.session_state.last_bid_vol:

```
drop = (
    st.session_state.last_bid_vol
    - total_bid
)

if drop > 500:

    st.warning(
        "🚨 買盤大量撤單"
    )
```

if st.session_state.last_ask_vol:

```
drop = (
    st.session_state.last_ask_vol
    - total_ask
)

if drop > 500:

    st.info(
        "🚨 賣盤大量撤單"
    )
```

st.session_state.last_bid_vol = total_bid
st.session_state.last_ask_vol = total_ask

# =========================

# 大戶追蹤

# =========================

if last_size >= big_order_size:

```
side = "Buy"

if bids and asks:

    best_bid = bids[0]["price"]
    best_ask = asks[0]["price"]

    trade_price = (
        quote.get("lastTrade", {})
        .get("price", current_price)
    )

    if trade_price <= best_bid:
        side = "Sell"

st.session_state.big_order_log.insert(
    0,
    {
        "time":datetime.now().strftime("%H:%M:%S"),
        "price":current_price,
        "qty":last_size,
        "side":side
    }
)
```

# =========================

# 大戶紀錄

# =========================

st.subheader("📜 大戶紀錄")

if st.session_state.big_order_log:

```
log_df = pd.DataFrame(
    st.session_state.big_order_log[:20]
)

st.dataframe(
    log_df,
    use_container_width=True,
    hide_index=True
)
```

else:

```
st.info("尚未偵測到大戶成交")
```
