# Streamlit GitHub 手機顯示端（V14.2 模擬交易 UI）

這個資料夾是手機 / Streamlit 顯示端，主要讀取 PC Worker 匯出的資料，不會送出真實委託。

## 新增功能

- V14 模擬交易 AI 摘要
- 上方券商 APP 風格「模擬成交快訊」跑馬燈
- 下方「交易明細」表格，最新資料固定在最上面
- 可下載交易明細 CSV
- 支援讀取 `data/dashboard_data.json` 裡的：
  - `latest_quotes`
  - `latest_signals`
  - `positions`
  - `paper_trades`
  - `daily_reports`
- 額外支援 `data/` 裡的 `paper_trades*.csv`、`backtest_trades*.csv` 作為交易明細來源

## 使用方式

1. 把 `streamlit_github` 資料夾推到 GitHub。
2. 到 Streamlit Cloud 部署。
3. PC Worker 匯出或同步以下檔案到 `streamlit_github/data/`：

```text
data/dashboard_data.json
data/current_model.json
```

如果有交易明細 CSV，也可以同步：

```text
data/paper_trades_YYYY-MM-DD.csv
data/backtest_trades_YYYY-MM-DD.csv
```

## 注意

`paper_trades` 會優先顯示在上方成交快訊與下方交易明細。若沒有 `paper_trades`，系統會用最新 AI 訊號顯示觀察提示。

此 Dashboard 僅作為模擬監控與分析，不是投資建議，也不會送出真實交易。
