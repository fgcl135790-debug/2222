# -*- coding: utf-8 -*-
"""
台股 AI 手機看盤 Dashboard / Streamlit GitHub 端

定位：
1. 手機端顯示 PC Worker 匯出的 AI 訊號、模擬持倉、模擬交易。
2. 新增手機端「AI 模擬交易看板」與券商 APP 風格成交快訊。
3. 交易明細一律最新在最上面。

提醒：這裡只做監控與模擬顯示，不會送出真實委託。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
LOCAL_DASHBOARD_PATH = DATA_DIR / "dashboard_data.json"
LOCAL_MODEL_PATH = DATA_DIR / "current_model.json"

st.set_page_config(
    page_title="台股 AI 模擬交易看盤",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# CSS：深色券商 APP 風格
# =========================
st.markdown(
    """
<style>
:root {
  --bg: #0b1220;
  --card: #111a2b;
  --card2: #16243a;
  --line: #2b3a55;
  --text: #f4f7fb;
  --muted: #9fb2cc;
  --red: #ff4d57;
  --green: #13d078;
  --blue: #2b7cff;
  --yellow: #ffd166;
}
.stApp { background: var(--bg); color: var(--text); }
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="stMetric"] {
  background: var(--card);
  border: 1px solid var(--line);
  padding: 12px 14px;
  border-radius: 14px;
}
[data-testid="stMetricValue"] { font-size: 1.6rem; }
.section-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px 16px;
  margin: 10px 0 16px 0;
}
.ai-pill {
  display: inline-block;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.85rem;
  font-weight: 700;
  margin-right: 8px;
}
.ai-long { background: rgba(255,77,87,.14); color: var(--red); border: 1px solid rgba(255,77,87,.55); }
.ai-short { background: rgba(19,208,120,.14); color: var(--green); border: 1px solid rgba(19,208,120,.55); }
.ai-watch { background: rgba(43,124,255,.14); color: #78a8ff; border: 1px solid rgba(43,124,255,.55); }
.trade-tape {
  position: sticky;
  top: 0;
  z-index: 999;
  background: linear-gradient(90deg, #0f1e33 0%, #172b49 45%, #0f1e33 100%);
  border: 1px solid #2e65b8;
  border-radius: 14px;
  padding: 10px 12px;
  margin: 8px 0 18px 0;
  box-shadow: 0 8px 22px rgba(0,0,0,.28);
  overflow: hidden;
}
.trade-tape-title {
  color: #9ec7ff;
  font-weight: 800;
  margin-bottom: 6px;
  letter-spacing: .5px;
}
.trade-tape-row {
  white-space: nowrap;
  overflow: hidden;
}
.trade-tape-track {
  display: inline-block;
  padding-left: 100%;
  animation: tape-scroll 38s linear infinite;
}
@keyframes tape-scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(-100%); }
}
.trade-chip {
  display: inline-block;
  background: #0b1322;
  border: 1px solid #365176;
  border-radius: 999px;
  padding: 6px 12px;
  margin-right: 10px;
  font-weight: 700;
}
.trade-win { color: var(--green); }
.trade-loss { color: var(--red); }
.trade-flat { color: var(--yellow); }
.small-muted { color: var(--muted); font-size: 0.9rem; }
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Data Loading
# =========================

def _safe_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def load_json_from_url(url: str) -> Dict[str, Any]:
    resp = requests.get(url, timeout=8)
    resp.raise_for_status()
    return resp.json()


def read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def load_dashboard_data() -> Dict[str, Any]:
    """讀取 PC Worker 匯出的 dashboard_data.json。"""
    url = _safe_secret("DASHBOARD_JSON_URL", "")
    if url:
        try:
            return load_json_from_url(url)
        except Exception as e:
            st.warning(f"遠端 DASHBOARD_JSON_URL 讀取失敗，改讀本地資料：{e}")

    if LOCAL_DASHBOARD_PATH.exists():
        try:
            return read_json_file(LOCAL_DASHBOARD_PATH)
        except Exception as e:
            st.warning(f"本地 dashboard_data.json 讀取失敗：{e}")

    model = read_json_file(LOCAL_MODEL_PATH) if LOCAL_MODEL_PATH.exists() else {}
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


def to_df(rows: Any) -> pd.DataFrame:
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    if isinstance(rows, list):
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)
    return pd.DataFrame()


def read_optional_trade_csvs() -> pd.DataFrame:
    """額外讀取 data 裡的交易明細 CSV。

    PC 端之後若同步 paper_trades_*.csv、backtest_trades_*.csv 到 Streamlit data，
    這裡會自動抓最新檔並顯示。
    """
    if not DATA_DIR.exists():
        return pd.DataFrame()
    patterns = [
        "paper_trades*.csv",
        "backtest_trades*.csv",
        "trades*.csv",
    ]
    files: List[Path] = []
    for p in patterns:
        files.extend(DATA_DIR.glob(p))
    if not files:
        return pd.DataFrame()
    files = sorted(set(files), key=lambda x: x.stat().st_mtime, reverse=True)
    frames = []
    for f in files[:3]:
        try:
            frames.append(pd.read_csv(f, encoding="utf-8-sig"))
        except Exception:
            try:
                frames.append(pd.read_csv(f))
            except Exception:
                pass
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["source_file"] = files[0].name
    return out


def first_existing(row: pd.Series, candidates: Iterable[str], default: Any = "") -> Any:
    for c in candidates:
        if c in row and pd.notna(row[c]) and row[c] != "":
            return row[c]
    return default


def normalize_action(x: Any) -> str:
    s = str(x or "").upper()
    if s in {"BUY", "LONG", "做多", "買進"}:
        return "BUY"
    if s in {"SELL", "SHORT", "做空", "賣出", "放空"}:
        return "SELL"
    if "SHORT" in s or "SELL" in s or "空" in s:
        return "SELL"
    if "BUY" in s or "LONG" in s or "多" in s or "買" in s:
        return "BUY"
    return str(x or "-")


def action_label(action: Any) -> str:
    a = normalize_action(action)
    if a == "BUY":
        return "🔴 BUY 做多"
    if a == "SELL":
        return "🟢 SELL 做空"
    return "⚪ 觀望"


def signal_badge(signal: Any) -> str:
    s = str(signal or "")
    if s in {"做多", "BUY", "LONG"} or "多" in s:
        return "🔴 做多"
    if s in {"做空", "SELL", "SHORT"} or "空" in s:
        return "🟢 做空"
    if "前兆" in s:
        return "🟡 攻擊前兆"
    return "⚪ 觀望"


def parse_time_like(value: Any) -> pd.Timestamp:
    if value is None or value == "" or pd.isna(value):
        return pd.NaT
    try:
        return pd.to_datetime(value)
    except Exception:
        try:
            return pd.to_datetime(str(value), format="%H:%M")
        except Exception:
            try:
                return pd.to_datetime(str(value), format="%H:%M:%S")
            except Exception:
                return pd.NaT


def sort_newest_trades(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    # 統一建立排序鍵，優先出場時間，其次進場時間，其次 ts / id。
    time_cols = ["exit_time", "closed_at", "entry_time", "opened_at", "ts", "time", "created_at"]
    sort_key = pd.Series([pd.NaT] * len(out), index=out.index, dtype="datetime64[ns]")
    for c in time_cols:
        if c in out.columns:
            parsed = out[c].apply(parse_time_like)
            sort_key = sort_key.fillna(parsed)
    out["_sort_time"] = sort_key
    if "id" in out.columns:
        out["_sort_id"] = pd.to_numeric(out["id"], errors="coerce").fillna(0)
    else:
        out["_sort_id"] = range(len(out))
    out = out.sort_values(["_sort_time", "_sort_id"], ascending=[False, False], na_position="last")
    return out.drop(columns=["_sort_time", "_sort_id"], errors="ignore")


def build_trade_view(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for _, r in df.iterrows():
        action = first_existing(r, ["action", "side", "signal"], "-")
        entry_time = first_existing(r, ["entry_time", "opened_at", "time", "ts"], "-")
        exit_time = first_existing(r, ["exit_time", "closed_at"], "-")
        entry_price = first_existing(r, ["entry_price", "entry_px", "price", "open_price"], "-")
        exit_price = first_existing(r, ["exit_price", "exit_px", "close_price"], "-")
        pnl_pct = first_existing(r, ["pnl_pct", "net_pnl_pct", "pnl%", "return_pct"], "")
        pnl = first_existing(r, ["pnl", "net_pnl", "profit", "profit_loss"], "")
        result = first_existing(r, ["result", "status"], "")
        reason = first_existing(r, ["reason", "exit_reason", "setup_type", "note"], "")
        rows.append(
            {
                "日期": first_existing(r, ["date", "trade_date"], ""),
                "動作": action_label(action),
                "分數": first_existing(r, ["score", "ai_score", "wave_score"], ""),
                "進場時間": entry_time,
                "進場價": entry_price,
                "出場時間": exit_time,
                "出場價": exit_price,
                "損益%": pnl_pct,
                "損益": pnl,
                "結果": result,
                "原因 / 型態": reason,
            }
        )
    return pd.DataFrame(rows)


def make_trade_tape(trades_df: pd.DataFrame, signals_df: pd.DataFrame, positions_df: pd.DataFrame) -> str:
    chips: List[str] = []
    if not trades_df.empty:
        latest = sort_newest_trades(trades_df).head(12)
        for _, r in latest.iterrows():
            action = normalize_action(first_existing(r, ["action", "side", "signal"], "-"))
            symbol = first_existing(r, ["symbol", "stock", "code"], "3481")
            entry_time = first_existing(r, ["entry_time", "opened_at", "time", "ts"], "-")
            entry_px = first_existing(r, ["entry_price", "entry_px", "price"], "-")
            exit_px = first_existing(r, ["exit_price", "exit_px"], "")
            pnl_pct = first_existing(r, ["pnl_pct", "net_pnl_pct", "pnl%"], "")
            try:
                pnl_num = float(str(pnl_pct).replace("%", ""))
            except Exception:
                pnl_num = 0.0
            cls = "trade-win" if pnl_num > 0 else "trade-loss" if pnl_num < 0 else "trade-flat"
            side = "做多" if action == "BUY" else "做空" if action == "SELL" else str(action)
            chips.append(
                f'<span class="trade-chip {cls}">{entry_time}｜{symbol}｜{side}｜進 {entry_px}｜出 {exit_px or "未出"}｜{pnl_pct}</span>'
            )
    elif not positions_df.empty:
        for _, r in positions_df.head(8).iterrows():
            symbol = first_existing(r, ["symbol", "stock", "code"], "-")
            side = first_existing(r, ["side", "action"], "-")
            px = first_existing(r, ["entry_price", "price", "avg_price"], "-")
            pnl = first_existing(r, ["unrealized_pnl_pct", "pnl_pct", "pnl"], "-")
            chips.append(f'<span class="trade-chip trade-flat">持倉｜{symbol}｜{side}｜{px}｜浮動 {pnl}</span>')
    elif not signals_df.empty:
        latest = signals_df.head(10)
        for _, r in latest.iterrows():
            symbol = first_existing(r, ["symbol", "stock", "code"], "-")
            sig = first_existing(r, ["signal", "action"], "觀望")
            score = first_existing(r, ["score", "ai_score"], "-")
            ts = first_existing(r, ["ts", "time"], "-")
            chips.append(f'<span class="trade-chip trade-flat">{ts}｜{symbol}｜{signal_badge(sig)}｜Score {score}</span>')
    if not chips:
        chips.append('<span class="trade-chip trade-flat">等待 PC Worker 同步成交 / 訊號資料</span>')

    return f"""
<div class="trade-tape">
  <div class="trade-tape-title">📣 模擬成交快訊</div>
  <div class="trade-tape-row"><div class="trade-tape-track">{''.join(chips)}</div></div>
</div>
"""


def make_price_chart(quotes: pd.DataFrame, symbol: str) -> go.Figure:
    q = quotes.copy()
    if "symbol" in q.columns:
        q = q[q["symbol"].astype(str) == str(symbol)].copy()
    if "ts" in q.columns:
        q = q.sort_values("ts")
    fig = go.Figure()
    if q.empty or "price" not in q.columns:
        fig.update_layout(title="尚無走勢資料", height=380, template="plotly_dark")
        return fig
    fig.add_trace(go.Scatter(x=q.get("ts", q.index), y=q["price"], mode="lines+markers", name="現價"))
    if "vwap" in q.columns:
        fig.add_trace(go.Scatter(x=q.get("ts", q.index), y=q["vwap"], mode="lines", name="VWAP"))
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=38, b=10),
        legend=dict(orientation="h"),
        template="plotly_dark",
    )
    return fig


def get_latest_per_symbol(signals_df: pd.DataFrame) -> pd.DataFrame:
    if signals_df.empty:
        return pd.DataFrame()
    out = signals_df.copy()
    if "id" in out.columns:
        out["_id"] = pd.to_numeric(out["id"], errors="coerce").fillna(0)
        out = out.sort_values("_id", ascending=False)
    elif "ts" in out.columns:
        out = out.sort_values("ts", ascending=False)
    if "symbol" in out.columns:
        out = out.drop_duplicates("symbol")
    return out.drop(columns=["_id"], errors="ignore")


def mobile_ai_summary(signals_df: pd.DataFrame, trades_df: pd.DataFrame, positions_df: pd.DataFrame) -> Dict[str, Any]:
    latest = get_latest_per_symbol(signals_df)
    active_positions = len(positions_df) if not positions_df.empty else 0
    today_trades = len(trades_df) if not trades_df.empty else 0
    latest_signal = "觀望"
    best_symbol = "-"
    best_score = "-"
    if not latest.empty:
        ranked = latest.copy()
        if "score" in ranked.columns:
            ranked["_score"] = pd.to_numeric(ranked["score"], errors="coerce").fillna(0)
            ranked = ranked.sort_values("_score", ascending=False)
        r = ranked.iloc[0]
        latest_signal = first_existing(r, ["signal", "action"], "觀望")
        best_symbol = first_existing(r, ["symbol", "stock", "code"], "-")
        best_score = first_existing(r, ["score", "ai_score"], "-")
    return {
        "active_positions": active_positions,
        "today_trades": today_trades,
        "latest_signal": latest_signal,
        "best_symbol": best_symbol,
        "best_score": best_score,
    }


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.header("控制台")
    refresh_on = st.toggle("自動刷新", value=True)
    refresh_sec = st.slider("刷新秒數", 3, 60, 10)
    show_raw = st.toggle("顯示原始資料區", value=False)
    st.caption("手機端只顯示 PC Worker 輸出的 AI 模擬結果，不會下真實委託。")

if refresh_on:
    st_autorefresh(interval=refresh_sec * 1000, key="dashboard_refresh")

# =========================
# Load Data
# =========================
data = load_dashboard_data()
model = data.get("model") or {}
quotes_df = to_df(data.get("latest_quotes", []))
signals_df = to_df(data.get("latest_signals", []))
positions_df = to_df(data.get("positions", []))
trades_df = to_df(data.get("paper_trades", []))
reports_df = to_df(data.get("daily_reports", []))

extra_trades_df = read_optional_trade_csvs()
if trades_df.empty and not extra_trades_df.empty:
    trades_df = extra_trades_df
elif not trades_df.empty and not extra_trades_df.empty:
    # 不去重，避免不同來源欄位不一致；只合併給使用者查看。
    trades_df = pd.concat([trades_df, extra_trades_df], ignore_index=True, sort=False)

trades_df = sort_newest_trades(trades_df)
if not signals_df.empty:
    signals_df = sort_newest_trades(signals_df)
if not positions_df.empty:
    positions_df = sort_newest_trades(positions_df)

ai_sum = mobile_ai_summary(signals_df, trades_df, positions_df)

# =========================
# Header + 成交快訊
# =========================
st.title("台股 AI 模擬交易看盤")
st.caption(
    f"資料更新：{data.get('exported_at', '尚無')}｜交易日：{data.get('trade_date', '')}｜模型：{model.get('version', '尚無模型')}"
)
st.markdown(make_trade_tape(trades_df, signals_df, positions_df), unsafe_allow_html=True)

# =========================
# AI 模擬交易摘要
# =========================
st.subheader("V14 模擬交易 AI")
mc1, mc2, mc3, mc4 = st.columns(4)
with mc1:
    st.metric("目前持倉", ai_sum["active_positions"])
with mc2:
    st.metric("今日模擬成交", ai_sum["today_trades"])
with mc3:
    st.metric("最高分股票", ai_sum["best_symbol"])
with mc4:
    st.metric("最高分", ai_sum["best_score"])

signal_class = "ai-watch"
if "多" in str(ai_sum["latest_signal"]) or str(ai_sum["latest_signal"]).upper() in {"BUY", "LONG"}:
    signal_class = "ai-long"
elif "空" in str(ai_sum["latest_signal"]) or str(ai_sum["latest_signal"]).upper() in {"SELL", "SHORT"}:
    signal_class = "ai-short"
st.markdown(
    f'<div class="section-card"><span class="ai-pill {signal_class}">{signal_badge(ai_sum["latest_signal"])}</span>'
    f'<span class="small-muted">手機端顯示 PC Worker 的模擬交易 AI；正式進出場以 paper_trades / positions 為主。</span></div>',
    unsafe_allow_html=True,
)

# =========================
# Main Metrics
# =========================
thresholds = model.get("thresholds", {}) if isinstance(model.get("thresholds", {}), dict) else {}
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("AI 模型日期", model.get("model_date", "-"))
with c2:
    st.metric("做多門檻", thresholds.get("long_score", "-"))
with c3:
    st.metric("停損%", thresholds.get("stop_loss_pct", "-"))
with c4:
    st.metric("停利%", thresholds.get("take_profit_pct", "-"))

# =========================
# 最新 AI 訊號 / 排行
# =========================
left, right = st.columns([1.05, 0.95])
with left:
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
        if "signal" in show.columns:
            show["訊號"] = show["signal"].apply(signal_badge)
        cols = [x for x in ["ts", "symbol", "name", "訊號", "score", "confidence", "理由"] if x in show.columns]
        if not cols:
            cols = show.columns.tolist()[:8]
        st.dataframe(show[cols], use_container_width=True, height=360)

with right:
    st.subheader("AI 選股排行")
    latest = get_latest_per_symbol(signals_df)
    if latest.empty:
        st.info("尚無排行資料。")
    else:
        if "score" in latest.columns:
            latest["_score"] = pd.to_numeric(latest["score"], errors="coerce").fillna(0)
            latest = latest.sort_values("_score", ascending=False).drop(columns=["_score"], errors="ignore")
        if "signal" in latest.columns:
            latest["訊號"] = latest["signal"].apply(signal_badge)
        ranking_cols = [x for x in ["symbol", "name", "訊號", "score", "confidence", "ts"] if x in latest.columns]
        st.dataframe(latest[ranking_cols].head(20), use_container_width=True, height=360)

# =========================
# Price Chart
# =========================
st.subheader("價格 / VWAP 走勢")
if not quotes_df.empty and "symbol" in quotes_df.columns:
    symbols = list(dict.fromkeys(quotes_df["symbol"].astype(str).tolist()))
    selected_symbol = st.selectbox("選擇股票", symbols)
    st.plotly_chart(make_price_chart(quotes_df, selected_symbol), use_container_width=True)
else:
    st.info("尚無行情資料。")

# =========================
# Positions / Trade Details
# =========================
left2, right2 = st.columns([0.9, 1.1])
with left2:
    st.subheader("模擬持倉")
    if positions_df.empty:
        st.info("目前沒有持倉資料。")
    else:
        st.dataframe(positions_df.head(30), use_container_width=True, height=330)

with right2:
    st.subheader("交易明細（最新在上）")
    if trades_df.empty:
        st.info("目前沒有模擬交易明細。")
    else:
        trade_view = build_trade_view(trades_df)
        st.dataframe(trade_view, use_container_width=True, height=420)
        csv = trade_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button("下載交易明細 CSV", csv, file_name="streamlit_trade_details_latest_first.csv", mime="text/csv")

# =========================
# Daily Reports / Notes
# =========================
st.subheader("每日績效報告")
if reports_df.empty:
    st.info("尚無每日報告。收盤後電腦端訓練完成才會產生。")
else:
    st.dataframe(sort_newest_trades(reports_df).head(20), use_container_width=True)

with st.expander("模型訓練備註"):
    notes = model.get("training_notes", [])
    if notes:
        for n in notes:
            st.write("-", n)
    else:
        st.write("尚無訓練備註。")

if show_raw:
    with st.expander("原始 dashboard_data.json"):
        st.json(data)

st.caption("提醒：本 dashboard 僅顯示電腦端 AI 模擬結果，不是投資建議，也不會送出真實交易。")
