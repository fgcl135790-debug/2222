import streamlit as st
import sys

st.title("Fugle 測試工具")

st.subheader("Python 版本")
st.code(sys.version)

# 測試 fugle_marketdata

st.subheader("fugle_marketdata")

try:
import fugle_marketdata

```
st.success("✅ fugle_marketdata 已載入")

st.write("模組內容：")
st.write(dir(fugle_marketdata))
```

except Exception as e:
st.error("❌ fugle_marketdata 載入失敗")
st.exception(e)

# 測試 websocket

st.subheader("WebSocket")

try:
from fugle_marketdata.websocket import WebSocketClient

```
st.success("✅ WebSocketClient 可使用")
st.write(WebSocketClient)
```

except Exception as e:
st.error("❌ WebSocketClient 不可使用")
st.exception(e)
