import streamlit as st
import sys

st.title("Fugle 環境測試")

# Python版本

st.subheader("Python Version")
st.code(sys.version)

# Fugle測試

st.subheader("Fugle MarketData")

try:
import fugle_marketdata

```
st.success("✅ fugle_marketdata 已安裝")

try:
    st.write("Module:")
    st.write(fugle_marketdata)
except:
    pass

try:
    st.write("dir(fugle_marketdata)")
    st.write(dir(fugle_marketdata))
except:
    pass
```

except Exception as e:

```
st.error("❌ fugle_marketdata 載入失敗")
st.exception(e)
```

# WebSocket測試

st.subheader("WebSocket 測試")

try:

```
from fugle_marketdata.websocket import WebSocketClient

st.success("✅ WebSocketClient 可使用")

st.write(WebSocketClient)
```

except Exception as e:

```
st.error("❌ WebSocketClient 不可使用")

st.exception(e)
```

# fugle_marketdata.websocket內容

st.subheader("websocket 模組內容")

try:

```
import fugle_marketdata.websocket as ws

st.success("✅ websocket 模組存在")

st.write(dir(ws))
```

except Exception as e:

```
st.error("❌ websocket 模組不存在")

st.exception(e)
```
