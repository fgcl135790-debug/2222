# Streamlit 手機端 V14.6 WebSocket 版

這版把手機端即時行情由 REST 輪詢改成 Fugle WebSocket。

## 使用方式

1. 部署 `streamlit_github` 到 GitHub / Streamlit Cloud。
2. Main file path 若 repo 根目錄是 `streamlit_github/`，請填：`streamlit_github/app.py`。
3. 手機打開後，在左側輸入 Fugle API Key 與股票代碼。
4. 按「啟動 WebSocket」。
5. WebSocket 會訂閱 `trades`、`books`、`candles`、`aggregates`，並用 V14 共用引擎做模擬交易。

## 注意

- Fugle 帳號方案必須支援 WebSocket，否則會在「WebSocket 連線紀錄」看到驗證或訂閱錯誤。
- 自動刷新秒數只是刷新畫面，行情本身由 WebSocket 推送，不再用 REST 每秒請求。
- 可按「下載本次 WebSocket real_quotes CSV」留存本次手機端收到的行情。
