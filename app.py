# -*- coding: utf-8 -*-
"""
台股 AI 手機看盤 Dashboard
Streamlit 端只負責顯示，不負責盤中長時間抓資料或訓練。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

APP_DIR = Path(__file__).resolve().parent
LOCAL_DASHBOARD_PATH = APP_DIR / "data" / "dashboard_data.json"
LOCAL_MODEL_PATH = APP_DIR / "data" / "current_model.json"

st.set_page_config(page_title="台股 AI 手機看盤", layout="wide")


def load_json_from_url(url: str) -> Dict[str, Any]:
    resp = requests.get(url, timeout=8)
    resp.raise_for_status()
    return resp.json()


def load_dashboard_data() -> Dict[str, Any]:
    """讀取電腦端輸出的 dashboard_data.json。

    優先順序：
    1. Streamlit secrets 裡的 DASHBOARD_JSON_URL
    2. 本 repo 的 data/dashboard_data.json
    3. 空資料 fallback
    """
    url = st.secrets.get("DASHBOARD_JSON_URL", "") if hasattr(st, "secrets") else ""
    if url:
        try:
            return load_json_from_url(url)
        except Exception as e:
            st.warning(f"遠端 DASHBOARD_JSON_URL 讀取失敗，改讀本地資料：{e}")

    if LOCAL_DASHBOARD_PATH.exists():
        try:
            return json.loads(LOCAL_DASHBOARD_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            st.warning(f"本地 dashboard_data.json 讀取失敗：{e}")

    model = {}
    if LOCAL_MODEL_PATH.exists():
        try:
            model = json.loads(LOCAL_MODEL_PATH.read_text(encoding="utf-8"))
        except Exception:
            model = {}
    return {
        "exported_at": "尚未匯出",
        "trade_date": "",
        "model": model,
        "latest_quotes": [],
        "latest_signals": [],
        "positions": [],
        "paper_trades": [],
        "daily_reports": [],
    }


def to_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def signal_badge(signal: str) -> str:
    if signal == "做多":
        return "🔴 做多"
    if signal == "做空":
        return "🟢 做空"
    return "⚪ 觀望"


def make_price_chart(quotes: pd.DataFrame, symbol: str) -> go.Figure:
    q = quotes[quotes["symbol"].astype(str) == str(symbol)].copy()
    q = q.sort_values("ts")
    fig = go.Figure()
    if q.empty:
        fig.update_layout(title="尚無走勢資料", height=420)
        return fig
    fig.add_trace(go.Scatter(x=q["ts"], y=q["price"], mode="lines+markers", name="現價"))
    if "vwap" in q.columns:
        fig.add_trace(go.Scatter(x=q["ts"], y=q["vwap"], mode="lines", name="VWAP"))
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h"))
    return fig


# 自動刷新，可在側邊欄關掉
with st.sidebar:
    st.header("控制台")
    refresh_on = st.toggle("自動刷新", value=True)
    refresh_sec = st.slider("刷新秒數", 3, 60, 10)
    st.caption("手機端只讀電腦端輸出的結果，不負責訓練。")

if refresh_on:
    st_autorefresh(interval=refresh_sec * 1000, key="dashboard_refresh")

data = load_dashboard_data()
model = data.get("model") or {}
quotes_df = to_df(data.get("latest_quotes", []))
signals_df = to_df(data.get("latest_signals", []))
positions_df = to_df(data.get("positions", []))
trades_df = to_df(data.get("paper_trades", []))
reports_df = to_df(data.get("daily_reports", []))

st.title("台股 AI 手機看盤")
st.caption(f"資料更新：{data.get('exported_at', '尚無')}｜交易日：{data.get('trade_date', '')}｜模型：{model.get('version', '尚無模型')}")

# 主要摘要
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("AI 模型日期", model.get("model_date", "-"))
with c2:
    st.metric("做多門檻", model.get("thresholds", {}).get("long_score", "-"))
with c3:
    st.metric("停損%", model.get("thresholds", {}).get("stop_loss_pct", "-"))
with c4:
    st.metric("停利%", model.get("thresholds", {}).get("take_profit_pct", "-"))

st.divider()

# 最新 AI 訊號
st.subheader("AI 即時判斷")
if signals_df.empty:
    st.info("尚無 AI 訊號。請先在電腦端啟動 Worker 並匯出 dashboard_data.json。")
else:
    show = signals_df.copy().head(20)
    if "reasons" in show.columns:
        def parse_reasons(x: Any) -> str:
            try:
                if isinstance(x, str):
                    arr = json.loads(x)
                else:
                    arr = x
                return "；".join(arr[:3]) if isinstance(arr, list) else str(x)
            except Exception:
                return str(x)
        show["理由"] = show["reasons"].apply(parse_reasons)
    show["訊號"] = show["signal"].apply(signal_badge)
    cols = [x for x in ["ts", "symbol", "name", "訊號", "score", "confidence", "理由"] if x in show.columns]
    st.dataframe(show[cols], use_container_width=True, height=420)

# 選股排行
st.subheader("今日 AI 選股排行")
if not signals_df.empty:
    latest = signals_df.sort_values("id", ascending=False).drop_duplicates("symbol")
    latest = latest.sort_values("score", ascending=False)
    ranking_cols = [x for x in ["symbol", "name", "signal", "score", "confidence", "ts"] if x in latest.columns]
    st.dataframe(latest[ranking_cols].head(20), use_container_width=True)

# 走勢圖
st.subheader("價格 / VWAP 走勢")
if not quotes_df.empty and "symbol" in quotes_df.columns:
    symbols = list(dict.fromkeys(quotes_df["symbol"].astype(str).tolist()))
    selected_symbol = st.selectbox("選擇股票", symbols)
    st.plotly_chart(make_price_chart(quotes_df, selected_symbol), use_container_width=True)
else:
    st.info("尚無行情資料。")

# 持倉與模擬交易
left, right = st.columns(2)
with left:
    st.subheader("模擬持倉")
    if positions_df.empty:
        st.info("目前沒有持倉資料。")
    else:
        st.dataframe(positions_df.head(30), use_container_width=True, height=280)

with right:
    st.subheader("模擬交易紀錄")
    if trades_df.empty:
        st.info("目前沒有模擬交易。")
    else:
        st.dataframe(trades_df.head(30), use_container_width=True, height=280)

st.subheader("每日績效報告")
if reports_df.empty:
    st.info("尚無每日報告。收盤後電腦端訓練完成才會產生。")
else:
    st.dataframe(reports_df.head(10), use_container_width=True)

with st.expander("模型訓練備註"):
    notes = model.get("training_notes", [])
    if notes:
        for n in notes:
            st.write("-", n)
    else:
        st.write("尚無訓練備註。")

st.caption("提醒：本 dashboard 僅顯示電腦端 AI 模擬結果，不是投資建議，也不會送出真實交易。")
