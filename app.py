from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import v14_engine

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MODEL_PATH = DATA_DIR / "current_model.json"
DASHBOARD_PATH = DATA_DIR / "dashboard_data.json"
TW_TZ = timezone(timedelta(hours=8))


def taiwan_now() -> datetime:
    return datetime.now(TW_TZ)

st.set_page_config(
    page_title="台股 AI 模擬交易看盤",
    page_icon="📣",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
:root { --card:#111c2e; --card2:#14365a; --blue:#2388ff; --red:#ff4b4b; --green:#19d37b; --muted:#9aa8bd; }
html, body, [class*="css"] { font-family: -apple-system, BlinkMacSystemFont, "Noto Sans TC", "Microsoft JhengHei", sans-serif; }
.block-container { padding-top: 1.2rem; max-width: 1180px; }
.big-title { font-size: 2.3rem; font-weight: 900; letter-spacing: .02em; margin-bottom: .2rem; }
.subtle { color: var(--muted); font-size: .92rem; }
.top-status { display:flex; flex-wrap:wrap; align-items:center; gap:7px; margin:.35rem 0 .8rem 0; color:#b9c8de; font-size:.9rem; }
.status-pill { border:1px solid #355c88; background:#0b1727; border-radius:999px; padding:4px 9px; font-weight:800; white-space:nowrap; }
.status-ok { color: var(--green); border-color:#1a8a58; }
.status-warn { color:#ffd166; border-color:#806a22; }
.status-bad { color: var(--red); border-color:#8a3333; }
.mini-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:8px 0 12px 0; }
.mini-card { background:var(--card); border:1px solid #263a59; border-radius:14px; padding:12px 14px; min-height:68px; }
.mini-title { color:#c9d7ee; font-size:.82rem; font-weight:800; }
.mini-value { font-size:1.28rem; font-weight:950; margin-top:5px; line-height:1.1; }
.signal-box { background:#11223a; border:1px solid #2c5d96; border-radius:14px; padding:12px 14px; margin:8px 0; }
.signal-main { font-weight:950; font-size:1.05rem; }
.signal-sub { color:#b9c8de; font-size:.86rem; margin-top:4px; }
.compact-warning { background:#3b4210; border:1px solid #626b18; color:#fff4a8; border-radius:12px; padding:10px 12px; margin:8px 0 12px; font-size:.88rem; line-height:1.5; }
.card { background: var(--card); border:1px solid #263a59; border-radius:16px; padding:16px; margin:8px 0; }
.card-blue { background: #12365a; border:1px solid #2374d5; border-radius:16px; padding:16px; margin:8px 0; }
.metric-title { color:#c9d7ee; font-size:.85rem; font-weight:700; }
.metric-value { font-size:1.8rem; font-weight:900; margin-top:4px; }
.good { color: var(--green); }
.bad { color: var(--red); }
.warn { color: #ffd166; }
.fill-tape { border:1px solid #2374d5; border-radius:16px; padding:14px 18px; margin:18px 0 22px 0; background:linear-gradient(90deg,#102441,#123b63); }
.fill-main { display:flex; flex-wrap:wrap; align-items:center; gap:12px; font-weight:900; font-size:1.05rem; }
.fill-pill { background:#07111f; border:1px solid #406b9e; color:#ffd166; border-radius:999px; padding:6px 12px; font-weight:900; }
.table-wrap { max-height: 420px; overflow:auto; border:1px solid #263a59; border-radius:12px; }
.small-note { color:#9aa8bd; font-size:.86rem; line-height:1.5; }
@media (max-width: 700px) {
  .big-title { font-size: 1.8rem; }
  .metric-value { font-size: 1.25rem; }
  .card { padding:10px; margin:6px 0; }
  .mini-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
  .mini-card { padding:10px 11px; min-height:58px; }
  .mini-value { font-size:1.12rem; }
  .fill-tape { margin:10px 0 14px 0; padding:12px; }
  .fill-main { gap:8px; font-size:.92rem; }
  .block-container { padding-top:.65rem; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# -----------------------------
# Helpers
# -----------------------------

def load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default


def fmt_price(x: Any) -> str:
    v = safe_float(x, math.nan)
    if math.isnan(v):
        return "-"
    return f"{v:.2f}" if abs(v) < 1000 else f"{v:,.0f}"


def fetch_fugle_quote(api_key: str, symbol: str, timeout: int = 8) -> Dict[str, Any]:
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol.strip()}"
    headers = {"X-API-KEY": api_key.strip()}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError("Fugle response is not JSON object")
    return data


def normalize_quote(raw: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    price = safe_float(raw.get("lastPrice") or raw.get("closePrice") or raw.get("price"), 0.0)
    vwap = safe_float(raw.get("avgPrice") or raw.get("averagePrice") or price, price)
    open_price = safe_float(raw.get("openPrice") or raw.get("open") or price, price)
    high = safe_float(raw.get("highPrice") or raw.get("high") or price, price)
    low = safe_float(raw.get("lowPrice") or raw.get("low") or price, price)
    last_size = safe_int(raw.get("lastSize") or raw.get("volume") or 0, 0)
    bids = raw.get("bids") if isinstance(raw.get("bids"), list) else []
    asks = raw.get("asks") if isinstance(raw.get("asks"), list) else []
    bid_size = sum(safe_int(x.get("size"), 0) for x in bids if isinstance(x, dict))
    ask_size = sum(safe_int(x.get("size"), 0) for x in asks if isinstance(x, dict))
    bid1 = safe_float(bids[0].get("price"), price) if bids and isinstance(bids[0], dict) else price
    ask1 = safe_float(asks[0].get("price"), price) if asks and isinstance(asks[0], dict) else price
    now = taiwan_now()
    return {
        "ts": now.strftime("%Y-%m-%d %H:%M:%S"),
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "symbol": symbol,
        "name": raw.get("name") or raw.get("symbolName") or symbol,
        "price": price,
        "vwap": vwap,
        "open": open_price,
        "high": high,
        "low": low,
        "last_size": last_size,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "bid1": bid1,
        "ask1": ask1,
        "raw": raw,
    }


def ensure_state() -> None:
    st.session_state.setdefault("quotes", {})
    st.session_state.setdefault("positions", [])
    st.session_state.setdefault("trades", [])
    st.session_state.setdefault("last_fill", None)
    st.session_state.setdefault("run_count", 0)
    st.session_state.setdefault("signals", [])
    st.session_state.setdefault("connection_status", "未連線")
    st.session_state.setdefault("last_update_tw", "-")
    st.session_state.setdefault("last_error", "")


def get_history(symbol: str) -> pd.DataFrame:
    rows = st.session_state.quotes.get(symbol, [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["vwap"] = pd.to_numeric(df["vwap"], errors="coerce")
    df["last_size"] = pd.to_numeric(df["last_size"], errors="coerce").fillna(0)
    df["bid_size"] = pd.to_numeric(df["bid_size"], errors="coerce").fillna(0)
    df["ask_size"] = pd.to_numeric(df["ask_size"], errors="coerce").fillna(0)
    return df


def compute_wave_signal(symbol: str, quote: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """手機端即時訊號也使用 v14_engine.py，避免和電腦版分歧。"""
    rows = st.session_state.quotes.get(symbol, [])
    if quote and (not rows or rows[-1] is not quote):
        rows = rows + [quote]
    try:
        bars = v14_engine.aggregate_real_quotes_to_1m(rows)
        fb = v14_engine.FeatureBuilder()
        feat = {}
        latest = None
        for b in bars:
            latest = b
            feat = fb.update(b)
        if latest is None:
            latest = quote
            feat = fb.update(quote)
        ok, cand = v14_engine.select_v14_candidate(latest, feat, settings)
        w = v14_engine.v14_wave_scores(latest, feat, settings)
        price = safe_float(latest.get("price"))
        action = cand.get("action") if ok and cand else "WAIT"
        score = cand.get("score") if ok and cand else max(w.get("long_score", 0), w.get("short_score", 0))
        return {
            "ts": latest.get("ts") or quote.get("ts"),
            "time": str(latest.get("ts") or quote.get("ts", ""))[11:19] if latest.get("ts") else quote.get("time"),
            "symbol": symbol,
            "name": latest.get("name") or quote.get("name", symbol),
            "price": price,
            "vwap": safe_float(feat.get("vwap"), safe_float(latest.get("vwap"), price)),
            "action": action,
            "score": round(float(score or 0), 1),
            "long_score": w.get("long_score", 0),
            "short_score": w.get("short_score", 0),
            "expected_net_pct": cand.get("expected_net_pct") if ok and cand else max(w.get("long_expected_net_pct", 0), w.get("short_expected_net_pct", 0)),
            "reason": cand.get("reason") if ok and cand else f"觀望 L{w.get('long_score',0):.0f}/S{w.get('short_score',0):.0f}",
            "setup_type": cand.get("setup_type") if ok and cand else "觀望",
            "vwap_gap": round(safe_float(feat.get("vwap_distance_pct")), 3),
            "ask_bid_ratio": round(1.0 / max(safe_float(feat.get("bid_ask_ratio"), 1.0), 0.0001), 3),
            "bid_ask_imbalance": round((safe_float(latest.get("total_bid") or latest.get("bid_size")) - safe_float(latest.get("total_ask") or latest.get("ask_size"))) / max(safe_float(latest.get("total_bid") or latest.get("bid_size")) + safe_float(latest.get("total_ask") or latest.get("ask_size")), 1.0), 3),
            "mom3": round(safe_float(feat.get("momentum_3_pct")), 3),
            "mom5": round(safe_float(feat.get("momentum_5_pct")), 3),
            "close_pos_5": round(safe_float(feat.get("close_position_pct")), 1),
        }
    except Exception as e:
        return {"symbol": symbol, "action": "WAIT", "score": 0, "reason": f"V14 shared engine error: {e}", "price": quote.get("price"), "vwap": quote.get("vwap")}


def has_open_position(symbol: str) -> bool:
    return any(p.get("symbol") == symbol and p.get("status") == "OPEN" for p in st.session_state.positions)


def open_position(signal: Dict[str, Any], settings: Dict[str, Any]) -> None:
    side = "LONG" if signal["action"] == "BUY" else "SHORT"
    price = safe_float(signal["price"])
    lots = int(settings["lots"])
    pos = {
        "id": f"{signal['symbol']}_{side}_{datetime.now().strftime('%H%M%S')}",
        "symbol": signal["symbol"], "name": signal.get("name", signal["symbol"]), "side": side, "status": "OPEN",
        "entry_time": signal["time"], "entry_ts": signal["ts"], "entry_price": price, "lots": lots,
        "score": signal["score"], "setup_type": signal["setup_type"], "reason": signal["reason"],
        "stop_loss_pct": settings["stop_loss_pct"], "take_profit_pct": settings["take_profit_pct"],
        "highest_pnl_pct": 0.0, "lowest_pnl_pct": 0.0,
    }
    st.session_state.positions.append(pos)
    fill = {
        "ts": signal["ts"], "time": signal["time"], "symbol": signal["symbol"], "name": pos["name"],
        "action": "BUY" if side == "LONG" else "SELL", "side": side,
        "price": price, "lots": lots, "event": "OPEN", "pnl_pct": "", "pnl": "", "reason": signal["reason"],
        "setup_type": signal["setup_type"], "score": signal["score"], "result": "OPEN",
    }
    st.session_state.last_fill = fill


def close_position(pos: Dict[str, Any], quote: Dict[str, Any], reason: str, settings: Dict[str, Any]) -> None:
    exit_price = safe_float(quote["price"])
    entry_price = safe_float(pos["entry_price"])
    if pos["side"] == "LONG":
        gross = (exit_price - entry_price) / entry_price * 100
        action = "SELL"
    else:
        gross = (entry_price - exit_price) / entry_price * 100
        action = "BUY"
    cost = settings["cost_pct"]
    pnl_pct = gross - cost
    pnl = round(entry_price * 1000 * int(pos["lots"]) * pnl_pct / 100)
    trade = {
        "date": quote["date"], "exit_ts": quote["ts"], "exit_time": quote["time"],
        "symbol": pos["symbol"], "name": pos.get("name", pos["symbol"]), "side": pos["side"],
        "action": action, "entry_time": pos["entry_time"], "entry_price": round(entry_price, 3),
        "exit_price": round(exit_price, 3), "lots": int(pos["lots"]), "score": pos.get("score", 0),
        "gross_pnl_pct": round(gross, 3), "cost_pct": round(cost, 3), "pnl_pct": round(pnl_pct, 3),
        "pnl": pnl, "result": "WIN" if pnl_pct > 0 else "LOSS", "exit_reason": reason,
        "setup_type": pos.get("setup_type", ""), "reason": pos.get("reason", ""),
    }
    st.session_state.trades.insert(0, trade)
    pos["status"] = "CLOSED"
    st.session_state.last_fill = {
        "ts": quote["ts"], "time": quote["time"], "symbol": pos["symbol"], "name": pos.get("name", pos["symbol"]),
        "action": action, "side": pos["side"], "price": exit_price, "lots": int(pos["lots"]),
        "event": "CLOSE", "pnl_pct": round(pnl_pct, 3), "pnl": pnl, "reason": reason,
        "setup_type": pos.get("setup_type", ""), "score": pos.get("score", 0), "result": trade["result"],
    }


def update_positions(quotes_by_symbol: Dict[str, Dict[str, Any]], settings: Dict[str, Any]) -> None:
    for pos in list(st.session_state.positions):
        if pos.get("status") != "OPEN":
            continue
        q = quotes_by_symbol.get(pos["symbol"])
        if not q:
            continue
        price = safe_float(q["price"])
        entry = safe_float(pos["entry_price"])
        gross = (price - entry) / entry * 100 if pos["side"] == "LONG" else (entry - price) / entry * 100
        pos["highest_pnl_pct"] = max(safe_float(pos.get("highest_pnl_pct")), gross)
        pos["lowest_pnl_pct"] = min(safe_float(pos.get("lowest_pnl_pct")), gross)
        # Hard stop/take profit.
        if gross <= -settings["stop_loss_pct"]:
            close_position(pos, q, "停損", settings)
            continue
        if gross >= settings["take_profit_pct"]:
            close_position(pos, q, "停利", settings)
            continue
        # Wave reversal exit: only if enough gross to cover cost + buffer.
        sig = compute_wave_signal(pos["symbol"], q, settings)
        min_rev = settings["min_reversal_exit_gross_pct"]
        if pos["side"] == "LONG" and sig["action"] == "SELL" and gross >= min_rev:
            close_position(pos, q, "波段轉空", settings)
        elif pos["side"] == "SHORT" and sig["action"] == "BUY" and gross >= min_rev:
            close_position(pos, q, "波段轉多", settings)


def maybe_open_positions(signals: List[Dict[str, Any]], settings: Dict[str, Any]) -> None:
    today = taiwan_now().strftime("%Y-%m-%d")
    today_trades = [t for t in st.session_state.trades if str(t.get("date")) == today]
    open_count = sum(1 for p in st.session_state.positions if p.get("status") == "OPEN")
    if len(today_trades) + open_count >= int(settings["max_daily_trades"]):
        return
    for sig in sorted(signals, key=lambda x: safe_float(x.get("score")), reverse=True):
        if sig["action"] not in ("BUY", "SELL"):
            continue
        if has_open_position(sig["symbol"]):
            continue
        if sig["action"] == "SELL" and not settings["allow_short"]:
            continue
        open_position(sig, settings)
        break


def render_metric(title: str, value: Any, cls: str = "") -> None:
    st.markdown(f"<div class='card'><div class='metric-title'>{title}</div><div class='metric-value {cls}'>{value}</div></div>", unsafe_allow_html=True)


def render_mini_grid(items: List[tuple]) -> None:
    html = ["<div class='mini-grid'>"]
    for title, value, cls in items:
        html.append(f"<div class='mini-card'><div class='mini-title'>{title}</div><div class='mini-value {cls}'>{value}</div></div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_trade_details(trades: List[Dict[str, Any]], height: int = 260) -> None:
    st.markdown("## 交易明細（最新在上）")
    if trades:
        trades_df = pd.DataFrame(trades)
        order_cols = ["date", "exit_time", "symbol", "name", "side", "action", "entry_time", "entry_price", "exit_price", "lots", "score", "gross_pnl_pct", "cost_pct", "pnl_pct", "pnl", "result", "exit_reason", "setup_type", "reason"]
        st.dataframe(trades_df[[c for c in order_cols if c in trades_df.columns]], use_container_width=True, hide_index=True, height=height)
        st.download_button("下載交易明細 CSV", trades_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"mobile_paper_trades_{taiwan_now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=True)
    else:
        st.markdown("<div class='card-blue'>目前沒有模擬交易明細。</div>", unsafe_allow_html=True)


def render_fill_tape() -> None:
    fill = st.session_state.last_fill
    if not fill:
        st.markdown("""
        <div class='fill-tape'>
          <div class='fill-main'>📣 模擬成交快訊 <span class='fill-pill'>等待即時訊號 / 尚未成交</span></div>
        </div>
        """, unsafe_allow_html=True)
        return
    color = "good" if fill.get("result") in ("WIN", "OPEN") else "bad"
    pnl_txt = ""
    if fill.get("event") == "CLOSE":
        pnl_txt = f"｜損益 {fill.get('pnl_pct')}% / {fill.get('pnl')} 元"
    st.markdown(f"""
    <div class='fill-tape'>
      <div class='fill-main'>
        📣 模擬成交快訊
        <span class='fill-pill'>{fill.get('time')} {fill.get('name')}({fill.get('symbol')})</span>
        <span>{fill.get('event')}｜{fill.get('action')}｜{fmt_price(fill.get('price'))}｜{fill.get('lots')} 張</span>
        <span class='{color}'>{pnl_txt}</span>
      </div>
      <div class='small-note'>{fill.get('setup_type','')}｜{fill.get('reason','')}</div>
    </div>
    """, unsafe_allow_html=True)


def make_price_chart(symbol: str) -> Optional[go.Figure]:
    df = get_history(symbol)
    if df.empty or len(df) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time"], y=df["price"], name="Price", mode="lines"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["vwap"], name="VWAP", mode="lines"))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=10), template="plotly_dark", legend=dict(orientation="h"))
    return fig


# -----------------------------
# Mobile real_quotes backtest
# -----------------------------

def _pick_col(df: pd.DataFrame, names: List[str]) -> Optional[str]:
    lowered = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lowered:
            return lowered[n.lower()]
    return None


def normalize_uploaded_real_quotes(uploaded_file: Any) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    return v14_engine.normalize_real_quotes_df(df)


def aggregate_quotes_to_1m_df(raw: pd.DataFrame) -> pd.DataFrame:
    rows = raw.to_dict("records") if isinstance(raw, pd.DataFrame) else []
    return pd.DataFrame(v14_engine.aggregate_real_quotes_to_1m(rows))


def compute_wave_signal_local(symbol: str, quote: Dict[str, Any], hist_rows: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    price = safe_float(quote.get("price"))
    vwap = safe_float(quote.get("vwap"), price)
    if price <= 0:
        return {"symbol": symbol, "action": "WAIT", "score": 0, "reason": "無有效價格"}
    bid_size = safe_float(quote.get("bid_size"), 0)
    ask_size = safe_float(quote.get("ask_size"), 0)
    ask_bid_ratio = ask_size / max(bid_size, 1.0)
    imbalance = (bid_size - ask_size) / max(bid_size + ask_size, 1.0)
    vwap_gap = (price - vwap) / vwap * 100 if vwap else 0.0
    prices = [safe_float(x.get("price")) for x in hist_rows if safe_float(x.get("price")) > 0]
    if not prices:
        prices = [price]
    def ret_n(n: int) -> float:
        if len(prices) <= n or prices[-n-1] == 0:
            return 0.0
        return (prices[-1] - prices[-n-1]) / prices[-n-1] * 100
    mom3 = ret_n(3)
    mom5 = ret_n(5)
    recent = prices[-5:] if len(prices) >= 5 else prices
    recent_high = max(recent) if recent else price
    recent_low = min(recent) if recent else price
    close_pos_5 = (price - recent_low) / max(recent_high - recent_low, 0.0001) * 100
    long_score = 0.0
    short_score = 0.0
    reasons_long: List[str] = []
    reasons_short: List[str] = []
    if vwap_gap < -0.7:
        long_score += 18; reasons_long.append("低於VWAP有反彈空間")
    if imbalance > 0.10:
        long_score += 18; reasons_long.append("買盤回補")
    if ask_bid_ratio < 1.25:
        long_score += 14; reasons_long.append("賣壓不厚")
    if mom3 > 0 and mom5 > -0.4:
        long_score += 18; reasons_long.append("短線由弱轉強")
    if close_pos_5 > 55:
        long_score += 12; reasons_long.append("5K位置轉強")
    if vwap_gap > settings["max_vwap_gap_long"]:
        long_score -= 35; reasons_long.append("離VWAP太遠不追高")
    if ask_bid_ratio > settings["max_ask_bid_for_long"] and imbalance < -0.25:
        long_score -= 45; reasons_long.append("高檔賣壓過厚禁止做多")
    if vwap_gap > 0.45:
        short_score += 18; reasons_short.append("高於VWAP有回落空間")
    if ask_bid_ratio > 1.8:
        short_score += 22; reasons_short.append("賣壓厚")
    if imbalance < -0.25:
        short_score += 20; reasons_short.append("買賣盤偏空")
    if close_pos_5 > 70 and mom3 <= 0.25:
        short_score += 18; reasons_short.append("高檔推進效率轉差")
    if mom3 < 0:
        short_score += 10; reasons_short.append("短線轉弱")
    if vwap_gap < -settings["max_vwap_gap_short"]:
        short_score -= 35; reasons_short.append("離VWAP過低不追空")
    long_expected = max(0.0, min(2.5, long_score / 100 * settings["take_profit_pct"] * 1.25))
    short_expected = max(0.0, min(2.8, short_score / 100 * settings["take_profit_pct"] * 1.35))
    min_expected = settings["min_expected_net_pct"]
    if short_score >= settings["entry_score"] and short_score >= long_score + 6 and short_expected >= min_expected:
        action = "SELL"; score = min(100.0, short_score); reason = "、".join(reasons_short[:4]); expected = short_expected; setup = "V14波段做空"
    elif long_score >= settings["entry_score"] and long_score > short_score + 6 and long_expected >= min_expected:
        action = "BUY"; score = min(100.0, long_score); reason = "、".join(reasons_long[:4]); expected = long_expected; setup = "V14波段做多"
    else:
        action = "WAIT"; score = max(long_score, short_score); reason = "觀望：波段分數或預估淨利不足"; expected = max(long_expected, short_expected); setup = "觀望"
    return {
        "ts": quote.get("ts"), "time": quote.get("time"), "date": quote.get("date"), "symbol": symbol, "name": quote.get("name", symbol),
        "price": price, "vwap": vwap, "action": action, "score": round(score, 1),
        "long_score": round(long_score, 1), "short_score": round(short_score, 1), "expected_net_pct": round(expected, 3),
        "reason": reason, "setup_type": setup, "vwap_gap": round(vwap_gap, 3), "ask_bid_ratio": round(ask_bid_ratio, 3),
        "bid_ask_imbalance": round(imbalance, 3), "mom3": round(mom3, 3), "mom5": round(mom5, 3), "close_pos_5": round(close_pos_5, 1),
    }


def run_uploaded_real_quotes_backtest(raw: pd.DataFrame, settings: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]:
    """手機端匯入 real_quotes 回測：直接呼叫共用 v14_engine。"""
    engine_settings = dict(settings)
    engine_settings.update({
        "direction_code": "AUTO",
        "v14_wave_model": True,
        "v14_only_wave_model": True,
        "v14_min_wave_score": settings.get("entry_score", 68.0),
        "v14_min_expected_net_pct": settings.get("min_expected_net_pct", 0.55),
        "v14_min_hold_profit_pct": settings.get("min_reversal_exit_gross_pct", 0.65),
        "paper_lots": settings.get("lots", 1),
        "allow_short_simulation": settings.get("allow_short", True),
        "allow_short": settings.get("allow_short", True),
        "tax_rate_pct": 0.15,
        "fee_discount": 1.0,
        "lot_size": 1000,
    })
    trades_df, summary, bars_df, sig_df = v14_engine.run_v14_backtest_from_dataframe(raw, engine_settings)
    return trades_df, summary, sig_df

# -----------------------------
# UI
# -----------------------------
ensure_state()
model = load_json(MODEL_PATH, {"model_name": "model_initial_v1", "model_date": "尚未同步", "version": "V14.4_SHARED_ENGINE"})
dashboard = load_json(DASHBOARD_PATH, {})

st.markdown("<div class='big-title'>台股 AI 模擬交易看盤</div>", unsafe_allow_html=True)
_now_tw = taiwan_now().strftime("%Y-%m-%d %H:%M:%S")
_conn = st.session_state.get("connection_status", "未連線")
_conn_cls = "status-ok" if "已連線" in _conn or "成功" in _conn else ("status-bad" if "失敗" in _conn or "錯誤" in _conn else "status-warn")
st.markdown(
    f"""
    <div class='top-status'>
      <span>手機端 V14.4 共用AI引擎</span>
      <span>模型：{model.get('model_name','-')}</span>
      <span>模型日期：{model.get('model_date','尚未同步')}</span>
      <span class='status-pill'>台灣時間：{_now_tw}</span>
      <span class='status-pill {_conn_cls}'>連線：{_conn}</span>
      <span class='status-pill'>最後更新：{st.session_state.get('last_update_tw','-')}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("手機端設定")
    api_key = st.text_input("Fugle API Key", type="password", help="只存在本次 Streamlit session，不寫入檔案。")
    symbols_text = st.text_input("監控股票代碼", value="3481", help="多檔請用逗號，例如 3481,2330,2303")
    refresh_now = st.button("立即更新 / 執行一次AI", use_container_width=True)
    auto_refresh = st.checkbox("自動刷新", value=False)
    refresh_sec = st.number_input("自動刷新秒數", min_value=1, max_value=60, value=1, step=1)
    st.divider()
    lots = st.number_input("每筆張數", min_value=1, max_value=100, value=1, step=1)
    max_daily_trades = st.number_input("每日最多模擬成交", min_value=1, max_value=50, value=8, step=1)
    allow_short = st.checkbox("允許做空模擬", value=True)
    entry_score = st.number_input("V14進場分數", min_value=30.0, max_value=100.0, value=52.0, step=1.0)
    stop_loss_pct = st.number_input("停損%", min_value=0.1, max_value=10.0, value=0.8, step=0.1)
    take_profit_pct = st.number_input("停利%", min_value=0.2, max_value=10.0, value=1.2, step=0.1)
    min_expected_net_pct = st.number_input("最低預估淨利%", min_value=0.0, max_value=5.0, value=0.55, step=0.05)
    if st.button("清空手機端模擬紀錄", use_container_width=True):
        st.session_state.positions = []
        st.session_state.trades = []
        st.session_state.last_fill = None
        st.rerun()

settings = {
    "lots": int(lots), "paper_lots": int(lots), "max_daily_trades": int(max_daily_trades), "requested_trade_count": 80,
    "allow_short": bool(allow_short), "allow_short_simulation": bool(allow_short),
    "entry_score": float(entry_score), "v14_min_wave_score": float(entry_score),
    "stop_loss_pct": float(stop_loss_pct), "take_profit_pct": float(take_profit_pct),
    "min_expected_net_pct": float(min_expected_net_pct), "v14_min_expected_net_pct": float(min_expected_net_pct),
    "cost_pct": 0.435, "v14_min_hold_profit_pct": 0.65,
    "min_reversal_exit_gross_pct": 0.65, "max_vwap_gap_long": 1.1, "max_vwap_gap_short": 3.5,
    "max_ask_bid_for_long": 2.0, "direction_code": "AUTO", "market_open": "09:00",
    "avoid_open_minutes": 5, "end_entry_minutes": 250, "max_holding_k": 45, "cooldown_k": 4,
    "lot_size": 1000, "fee_discount": 1.0, "tax_rate_pct": 0.15,
}

render_fill_tape()

run_reason = refresh_now or (auto_refresh and bool(api_key))
symbols = [s.strip() for s in symbols_text.replace("，", ",").split(",") if s.strip()]
quotes_now: Dict[str, Dict[str, Any]] = {}
signals_now: List[Dict[str, Any]] = []

if run_reason and api_key and symbols:
    any_error = False
    for symbol in symbols:
        try:
            raw = fetch_fugle_quote(api_key, symbol)
            q = normalize_quote(raw, symbol)
            st.session_state.quotes.setdefault(symbol, []).append(q)
            st.session_state.quotes[symbol] = st.session_state.quotes[symbol][-360:]
            quotes_now[symbol] = q
        except Exception as e:
            any_error = True
            st.session_state.last_error = str(e)
            st.error(f"{symbol} 即時報價失敗：{e}")
    if quotes_now:
        st.session_state.connection_status = "已連線" if not any_error else "部分成功"
        st.session_state.last_update_tw = taiwan_now().strftime("%H:%M:%S")
    elif any_error:
        st.session_state.connection_status = "連線失敗"
    if quotes_now:
        update_positions(quotes_now, settings)
        for symbol, q in quotes_now.items():
            signals_now.append(compute_wave_signal(symbol, q, settings))
        st.session_state.signals = signals_now
        maybe_open_positions(signals_now, settings)
        st.session_state.run_count += 1
elif not api_key:
    st.info("請在左側輸入 Fugle API Key，手機端就能直接用即時股市資料跑 V14 模擬交易。")
else:
    signals_now = st.session_state.get("signals", [])

open_positions = [p for p in st.session_state.positions if p.get("status") == "OPEN"]
trades = st.session_state.trades
best_sig = max(st.session_state.get("signals", []), key=lambda x: safe_float(x.get("score")), default={})

st.markdown("## V14 模擬交易 AI")
render_mini_grid([
    ("目前持倉", len(open_positions), ""),
    ("今日成交", len(trades), ""),
    ("最高分股票", f"{best_sig.get('name','-')} {best_sig.get('symbol','')}", ""),
    ("最高分", best_sig.get("score", "-"), ""),
    ("AI模型日期", model.get("model_date", "尚未同步"), ""),
    ("做多門檻", settings["entry_score"], ""),
    ("停損%", settings["stop_loss_pct"], ""),
    ("停利%", settings["take_profit_pct"], ""),
])

if model.get("model_date") in (None, "", "尚未同步") or str(model.get("model_date", "")).startswith("2026-06-30"):
    st.markdown("<div class='compact-warning'>AI 模型日期尚未同步或仍是舊資料。現在不用急著更新也可以測即時模擬與 real_quotes 回測；等 PC Worker 收盤訓練完成後，再同步 models/current_model.json 到 streamlit_github/data/current_model.json，模型日期才會更新。</div>", unsafe_allow_html=True)

st.markdown("## AI 即時判斷")
if st.session_state.get("signals"):
    sig_df = pd.DataFrame(st.session_state.signals)
    top = best_sig or st.session_state.signals[0]
    action_txt = {"BUY":"做多", "SELL":"做空", "WAIT":"觀望"}.get(top.get("action"), top.get("action", "-"))
    action_cls = "good" if top.get("action") == "BUY" else ("bad" if top.get("action") == "SELL" else "warn")
    st.markdown(f"""
    <div class='signal-box'>
      <div class='signal-main'><span class='{action_cls}'>{action_txt}</span>｜{top.get('name','-')} {top.get('symbol','')}｜Score {top.get('score','-')}｜{fmt_price(top.get('price'))}</div>
      <div class='signal-sub'>{top.get('setup_type','')}｜{top.get('reason','')}</div>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("查看完整 AI 訊號表", expanded=False):
        show_cols = ["time", "symbol", "name", "action", "score", "long_score", "short_score", "price", "vwap", "vwap_gap", "ask_bid_ratio", "bid_ask_imbalance", "expected_net_pct", "setup_type", "reason"]
        st.dataframe(sig_df[[c for c in show_cols if c in sig_df.columns]], use_container_width=True, hide_index=True, height=220)
else:
    st.markdown("<div class='card-blue'>尚無 AI 訊號。請輸入 API Key 後按「立即更新 / 執行一次AI」。</div>", unsafe_allow_html=True)

render_trade_details(trades, height=260)

chart_symbol = symbols[0] if symbols else "3481"
fig = make_price_chart(chart_symbol)
if fig:
    with st.expander("價格 / VWAP 走勢", expanded=False):
        st.plotly_chart(fig, use_container_width=True)

st.markdown("## 模擬持倉")
if open_positions:
    rows = []
    for p in open_positions:
        q = get_history(p["symbol"])
        last_price = safe_float(q.iloc[-1]["price"]) if not q.empty else safe_float(p["entry_price"])
        entry = safe_float(p["entry_price"])
        pnl_pct = (last_price - entry) / entry * 100 if p["side"] == "LONG" else (entry - last_price) / entry * 100
        rows.append({**p, "last_price": round(last_price, 3), "unrealized_pct": round(pnl_pct, 3)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.markdown("<div class='card-blue'>目前沒有持倉資料。</div>", unsafe_allow_html=True)

st.markdown("## 匯入 real_quotes 回測")
st.markdown("<div class='small-note'>手機端可直接上傳 PC Worker 產生的 real_quotes_*.csv，呼叫與電腦端共用的 v14_engine.py 回測，讓手機與電腦使用同一套核心判斷。</div>", unsafe_allow_html=True)
uploaded_real_quotes = st.file_uploader("上傳 real_quotes CSV", type=["csv"], key="real_quotes_backtest_uploader")
backtest_run = st.button("執行手機端 real_quotes 回測", use_container_width=True)
if uploaded_real_quotes is not None:
    st.caption(f"已選擇：{uploaded_real_quotes.name}")
if backtest_run and uploaded_real_quotes is not None:
    try:
        raw_bt = normalize_uploaded_real_quotes(uploaded_real_quotes)
        bt_trades, bt_summary, bt_signals = run_uploaded_real_quotes_backtest(raw_bt, settings)
        st.session_state["uploaded_backtest_trades"] = bt_trades
        st.session_state["uploaded_backtest_summary"] = bt_summary
        st.session_state["uploaded_backtest_signals"] = bt_signals
    except Exception as e:
        st.error(f"real_quotes 回測失敗：{e}")

bt_summary = st.session_state.get("uploaded_backtest_summary")
bt_trades = st.session_state.get("uploaded_backtest_trades")
if isinstance(bt_summary, dict):
    c = st.columns(5)
    c[0].metric("1分K數", bt_summary.get("bars", 0))
    c[1].metric("交易筆數", bt_summary.get("trades", 0))
    c[2].metric("勝率", f"{bt_summary.get('win_rate', 0)}%")
    c[3].metric("總損益", f"{bt_summary.get('total_pnl', 0):,}")
    c[4].metric("總損益%", f"{bt_summary.get('total_pnl_pct', 0)}%")
if isinstance(bt_trades, pd.DataFrame) and not bt_trades.empty:
    st.dataframe(bt_trades, use_container_width=True, hide_index=True, height=360)
    st.download_button(
        "下載手機端 real_quotes 回測明細 CSV",
        bt_trades.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"mobile_real_quotes_backtest_{taiwan_now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
elif isinstance(bt_summary, dict):
    st.markdown("<div class='card-blue'>這次 real_quotes 回測沒有產生交易。</div>", unsafe_allow_html=True)

st.markdown("## 每日績效報告")
if trades:
    df = pd.DataFrame(trades)
    wins = (df["pnl_pct"] > 0).sum()
    total = len(df)
    total_pnl = df["pnl"].sum()
    avg_pct = df["pnl_pct"].mean()
    c = st.columns(4)
    c[0].metric("交易筆數", total)
    c[1].metric("勝率", f"{wins / total * 100:.1f}%")
    c[2].metric("總損益", f"{total_pnl:,.0f}")
    c[3].metric("平均每筆%", f"{avg_pct:.3f}%")
else:
    st.markdown("<div class='card-blue'>尚無每日報告。</div>", unsafe_allow_html=True)

with st.expander("模型訓練備註"):
    st.json(model)
    st.markdown("手機端可以直接跑即時模擬，但正式長時間訓練與收盤後強化，仍建議由 PC Worker 負責，並同步 current_model.json 與 dashboard_data.json。")

if auto_refresh and api_key:
    time.sleep(int(refresh_sec))
    st.rerun()
