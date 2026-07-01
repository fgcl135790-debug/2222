# 台股 AI 模擬交易看盤 Streamlit 手機版 V14.3

## 功能
- 手機端可輸入 Fugle API Key。
- 使用 Fugle REST 即時報價進行模擬交易。
- V14 WaveScore 模擬交易邏輯：做多不追高、做空偵測高檔假強勢、波段式出場。
- 上方券商 APP 風格成交快訊。
- 下方交易明細最新在上。

## Streamlit Cloud 設定
Main file path：

```text
streamlit_github/app.py
```

如果 repo 根目錄就是 app.py，才填：

```text
app.py
```

## 注意
手機端的 API Key 使用 password input，不會寫入檔案。
手機端模擬交易是該瀏覽器 session 狀態；重新整理或重啟 app 可能會清空。正式長時間紀錄仍建議由 PC Worker 跑盤後同步資料。
