# 台股 AI 手機看盤：GitHub / Streamlit 端

這個資料夾是「手機端 Dashboard」。它只負責顯示電腦端 Worker 輸出的資料，不負責長時間抓資料、模擬交易或訓練。

---

## 1. 本機測試

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 2. 上傳 GitHub

把這個資料夾內容上傳到一個 GitHub repo，例如：

```text
stock-ai-streamlit-dashboard
```

repo 至少要有：

```text
app.py
requirements.txt
data/dashboard_data.json
data/current_model.json
```

---

## 3. 部署到 Streamlit Community Cloud

1. 登入 Streamlit Community Cloud
2. 選 GitHub repo
3. Branch 選 main
4. Main file path 選 `app.py`
5. Deploy

部署後手機開 Streamlit 給你的網址即可。

---

## 4. 和電腦端同步資料

電腦端 Worker 會產生：

```text
exports/dashboard_data.json
models/current_model.json
```

請把它們同步到這個 Streamlit 專案：

```text
data/dashboard_data.json
data/current_model.json
```

你可以在電腦端 GUI 填入這個 Streamlit 專案資料夾路徑，讓它自動複製。

---

## 5. Streamlit Secrets 選項

如果你之後把 `dashboard_data.json` 放到一個固定網址，也可以在 Streamlit Cloud 的 Secrets 設定：

```toml
DASHBOARD_JSON_URL = "https://你的固定資料網址/dashboard_data.json"
```

設定後 `app.py` 會優先讀這個遠端 JSON。

---

## 6. 目前第一版限制

第一版是檔案同步模式：

```text
電腦 Worker -> dashboard_data.json -> GitHub / Streamlit -> 手機看盤
```

如果要做到手機端幾乎即時更新，下一版建議升級成：

```text
電腦 Worker -> Supabase/PostgreSQL -> Streamlit Cloud -> 手機
```

---

## 7. 注意

這是 AI 模擬交易與監控 dashboard，不是投資建議，也不會送出真實委託單。
