# -*- coding: utf-8 -*-
"""Shared V14.4 Wave Trading Engine.

This file is copied into both pc_worker and streamlit_github.
Both desktop backtest and mobile real_quotes upload should call these functions so
same real_quotes input produces the same trades.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

TZ = timezone(timedelta(hours=8))


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or x == "":
            return default
        if isinstance(x, float) and math.isnan(x):
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


def parse_ts(value: Any) -> datetime:
    s = str(value or "").strip()
    if not s:
        return datetime.now(TZ)
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        # common CSV fallback
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = datetime.now(TZ)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def minutes_after_market_open(ts: Any, market_open: str = "09:00") -> int:
    try:
        dt = parse_ts(ts)
        hh, mm = str(market_open or "09:00").split(":")[:2]
        open_dt = dt.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        return int((dt - open_dt).total_seconds() // 60)
    except Exception:
        return 0


def compute_trade_cost(entry_price: float, exit_price: float, qty_lots: int = 1, lot_size: int = 1000, fee_discount: float = 1.0, tax_rate_pct: float = 0.15) -> Dict[str, float]:
    qty_shares = max(0, int(qty_lots)) * max(1, int(lot_size))
    entry_notional = max(0.0, safe_float(entry_price)) * qty_shares
    exit_notional = max(0.0, safe_float(exit_price)) * qty_shares
    discount = max(0.0, safe_float(fee_discount, 1.0))
    tax_rate = max(0.0, safe_float(tax_rate_pct, 0.15)) / 100.0
    broker_fee_rate = 0.001425 * discount
    fee = (entry_notional + exit_notional) * broker_fee_rate
    tax = exit_notional * tax_rate
    total = fee + tax
    base = entry_notional if entry_notional > 0 else 1.0
    return {
        "entry_notional": round(entry_notional, 2),
        "exit_notional": round(exit_notional, 2),
        "fee_amount": round(fee, 2),
        "tax_amount": round(tax, 2),
        "cost_amount": round(total, 2),
        "cost_pct": round(total / base * 100, 4),
    }


def ema(values: List[float], span: int) -> float:
    vals = [safe_float(v) for v in values if safe_float(v) > 0]
    if not vals:
        return 0.0
    if len(vals) == 1:
        return vals[-1]
    alpha = 2 / (span + 1)
    e = vals[0]
    for v in vals[1:]:
        e = v * alpha + e * (1 - alpha)
    return float(e)


def pick_col(columns: Iterable[Any], names: List[str]) -> Optional[Any]:
    lowered = {str(c).strip().lower(): c for c in columns}
    for n in names:
        if n.lower() in lowered:
            return lowered[n.lower()]
    return None


def normalize_real_quotes_df(df: Any) -> Any:
    """Normalize PC real_quotes CSV into canonical columns."""
    if pd is None:
        raise RuntimeError("pandas is required")
    if df is None or len(df) == 0:
        return pd.DataFrame()
    ts_col = pick_col(df.columns, ["ts", "time", "datetime", "date_time"])
    date_col = pick_col(df.columns, ["trade_date", "date"])
    symbol_col = pick_col(df.columns, ["symbol", "stock", "code"])
    name_col = pick_col(df.columns, ["name", "stock_name"])
    price_col = pick_col(df.columns, ["price", "close", "lastprice", "closeprice", "lastPrice", "closePrice"])
    vwap_col = pick_col(df.columns, ["vwap", "avgprice", "averageprice", "avgPrice", "averagePrice"])
    high_col = pick_col(df.columns, ["high", "highprice", "highPrice"])
    low_col = pick_col(df.columns, ["low", "lowprice", "lowPrice"])
    size_col = pick_col(df.columns, ["last_size", "lastsize", "lastSize", "volume"])
    bid_col = pick_col(df.columns, ["total_bid", "bid_size", "bid", "totalBid"])
    ask_col = pick_col(df.columns, ["total_ask", "ask_size", "ask", "totalAsk"])
    if ts_col is None or price_col is None:
        raise ValueError("real_quotes CSV 必須至少包含 ts/time 與 price/close 欄位。")
    out = pd.DataFrame()
    out["ts"] = df[ts_col].astype(str)
    out["dt"] = pd.to_datetime(out["ts"], errors="coerce")
    # pandas may fail timezone mixed; fallback row by row
    if out["dt"].isna().all():
        out["dt"] = [parse_ts(x) for x in out["ts"]]
    out["trade_date"] = df[date_col].astype(str) if date_col is not None else out["dt"].dt.strftime("%Y-%m-%d")
    out["symbol"] = df[symbol_col].astype(str) if symbol_col is not None else "3481"
    out["name"] = df[name_col].astype(str) if name_col is not None else out["symbol"]
    out["price"] = pd.to_numeric(df[price_col], errors="coerce")
    out["vwap"] = pd.to_numeric(df[vwap_col], errors="coerce") if vwap_col is not None else out["price"]
    out["high"] = pd.to_numeric(df[high_col], errors="coerce") if high_col is not None else out["price"]
    out["low"] = pd.to_numeric(df[low_col], errors="coerce") if low_col is not None else out["price"]
    out["last_size"] = pd.to_numeric(df[size_col], errors="coerce").fillna(0) if size_col is not None else 0
    out["total_bid"] = pd.to_numeric(df[bid_col], errors="coerce").fillna(0) if bid_col is not None else 0
    out["total_ask"] = pd.to_numeric(df[ask_col], errors="coerce").fillna(0) if ask_col is not None else 0
    out = out.dropna(subset=["dt", "price"]).copy()
    out = out[out["price"] > 0]
    out = out.sort_values(["dt", "symbol"]).reset_index(drop=True)
    return out


def normalize_real_quotes_records(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    if pd is not None:
        try:
            df = normalize_real_quotes_df(pd.DataFrame(rows))
            return df.to_dict("records")
        except Exception:
            pass
    out = []
    for r in rows:
        price = safe_float(r.get("price") or r.get("close") or r.get("lastPrice") or r.get("closePrice"))
        if price <= 0:
            continue
        dt = parse_ts(r.get("ts") or r.get("time") or r.get("datetime"))
        out.append({
            "ts": dt.isoformat(),
            "dt": dt,
            "trade_date": str(r.get("trade_date") or r.get("date") or dt.date().isoformat())[:10],
            "symbol": str(r.get("symbol") or r.get("stock") or r.get("code") or "3481"),
            "name": r.get("name") or r.get("stock_name") or r.get("symbol") or "3481",
            "price": price,
            "vwap": safe_float(r.get("vwap") or r.get("avgPrice") or r.get("averagePrice"), price),
            "high": safe_float(r.get("high") or r.get("highPrice"), price),
            "low": safe_float(r.get("low") or r.get("lowPrice"), price),
            "last_size": safe_int(r.get("last_size") or r.get("lastSize") or r.get("volume")),
            "total_bid": safe_int(r.get("total_bid") or r.get("bid_size") or r.get("bid")),
            "total_ask": safe_int(r.get("total_ask") or r.get("ask_size") or r.get("ask")),
        })
    out.sort(key=lambda x: (x["dt"], x["symbol"]))
    return out


def aggregate_real_quotes_to_1m(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate real_quotes snapshots to 1m OHLCV with average depth.

    Matches desktop V14.3 behavior: last price/vwap in each minute, average total_bid/ask.
    """
    norm = normalize_real_quotes_records(rows)
    buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
    order: List[Tuple[str, str]] = []
    for r in norm:
        symbol = str(r.get("symbol") or "").strip()
        if not symbol:
            continue
        dt = r.get("dt") if isinstance(r.get("dt"), datetime) else parse_ts(r.get("ts"))
        minute_dt = dt.replace(second=0, microsecond=0)
        minute_key = minute_dt.isoformat()
        key = (symbol, minute_key)
        price = safe_float(r.get("price"))
        if price <= 0:
            continue
        if key not in buckets:
            buckets[key] = {
                "ts": minute_key,
                "trade_date": str(r.get("trade_date") or minute_dt.date().isoformat())[:10],
                "symbol": symbol,
                "name": r.get("name") or symbol,
                "open": price,
                "high": price,
                "low": price,
                "price": price,
                "vwap": safe_float(r.get("vwap"), price),
                "last_size": 0,
                "total_bid_sum": 0.0,
                "total_ask_sum": 0.0,
                "depth_n": 0,
            }
            order.append(key)
        b = buckets[key]
        b["high"] = max(safe_float(b.get("high")), price)
        b["low"] = min(safe_float(b.get("low")), price)
        b["price"] = price
        if safe_float(r.get("vwap")) > 0:
            b["vwap"] = safe_float(r.get("vwap"))
        b["last_size"] = safe_int(b.get("last_size")) + max(0, safe_int(r.get("last_size")))
        tb = safe_float(r.get("total_bid"))
        ta = safe_float(r.get("total_ask"))
        if tb > 0 or ta > 0:
            b["total_bid_sum"] += tb
            b["total_ask_sum"] += ta
            b["depth_n"] += 1
    out: List[Dict[str, Any]] = []
    for key in order:
        b = dict(buckets[key])
        n = max(1, safe_int(b.pop("depth_n", 0)))
        total_bid_sum = safe_float(b.pop("total_bid_sum", 0.0))
        total_ask_sum = safe_float(b.pop("total_ask_sum", 0.0))
        b["total_bid"] = int(total_bid_sum / n) if total_bid_sum > 0 else 0
        b["total_ask"] = int(total_ask_sum / n) if total_ask_sum > 0 else 0
        out.append(b)
    return out


class FeatureBuilder:
    def __init__(self) -> None:
        self.prices: Dict[str, List[float]] = {}
        self.highs: Dict[str, List[float]] = {}
        self.lows: Dict[str, List[float]] = {}
        self.volumes: Dict[str, List[float]] = {}
        self.session_key: Dict[str, str] = {}
        self.session_pv: Dict[str, float] = {}
        self.session_vol: Dict[str, float] = {}

    def update(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        symbol = str(quote.get("symbol") or "")
        price = safe_float(quote.get("price"))
        volume_now = safe_int(quote.get("last_size"))
        high_now = safe_float(quote.get("high"), price) or price
        low_now = safe_float(quote.get("low"), price) or price
        open_now = safe_float(quote.get("open"), price) or price
        trade_date_key = str(quote.get("trade_date") or str(quote.get("ts", ""))[:10])
        if self.session_key.get(symbol) != trade_date_key:
            self.session_key[symbol] = trade_date_key
            self.session_pv[symbol] = 0.0
            self.session_vol[symbol] = 0.0
        typical_price = (high_now + low_now + price) / 3.0 if high_now > 0 and low_now > 0 else price
        vol_for_vwap = float(volume_now if volume_now > 0 else 1)
        self.session_pv[symbol] = self.session_pv.get(symbol, 0.0) + typical_price * vol_for_vwap
        self.session_vol[symbol] = self.session_vol.get(symbol, 0.0) + vol_for_vwap
        rolling_vwap = self.session_pv[symbol] / self.session_vol[symbol] if self.session_vol[symbol] > 0 else price

        self.prices.setdefault(symbol, []).append(price)
        self.highs.setdefault(symbol, []).append(high_now)
        self.lows.setdefault(symbol, []).append(low_now)
        self.volumes.setdefault(symbol, []).append(volume_now)
        self.prices[symbol] = self.prices[symbol][-500:]
        self.highs[symbol] = self.highs[symbol][-500:]
        self.lows[symbol] = self.lows[symbol][-500:]
        self.volumes[symbol] = self.volumes[symbol][-500:]

        prices = self.prices[symbol]
        highs = self.highs[symbol]
        lows = self.lows[symbol]
        vols = self.volumes[symbol]
        recent_high_20 = highs[-20:] if highs else [price]
        recent_low_20 = lows[-20:] if lows else [price]
        recent_5 = prices[-5:] if prices else [price]
        prev_high = max(recent_high_20[:-1]) if len(recent_high_20) >= 2 else price
        prev_low = min(recent_low_20[:-1]) if len(recent_low_20) >= 2 else price
        recent_high_10 = highs[-10:] if highs else [price]
        recent_low_10 = lows[-10:] if lows else [price]
        prev_high_10 = max(recent_high_10[:-1]) if len(recent_high_10) >= 2 else price
        prev_low_10 = min(recent_low_10[:-1]) if len(recent_low_10) >= 2 else price
        is_breakout = price > prev_high if len(recent_high_20) >= 2 else False
        is_near_breakout = price >= prev_high_10 * 0.995 if prev_high_10 > 0 and len(recent_high_10) >= 2 else False
        volume_avg = sum(vols[-100:]) / max(1, len(vols[-100:]))
        volume_ratio = volume_now / volume_avg if volume_avg > 0 else 1.0
        range20_pct = ((max(recent_high_20) / min(recent_low_20)) - 1) * 100 if min(recent_low_20) > 0 else 0.0
        range5_pct = ((max(recent_5) / min(recent_5)) - 1) * 100 if min(recent_5) > 0 else 0.0
        momentum_3_pct = (price / prices[-4] - 1) * 100 if len(prices) >= 4 and prices[-4] > 0 else 0.0
        momentum_5_pct = (price / prices[-6] - 1) * 100 if len(prices) >= 6 and prices[-6] > 0 else 0.0
        recent_peak_10 = max(recent_high_10) if recent_high_10 else price
        recent_peak_pullback_pct = (price / recent_peak_10 - 1) * 100 if recent_peak_10 > 0 else 0.0
        bid = safe_float(quote.get("total_bid") if quote.get("total_bid") is not None else quote.get("bid_size"))
        ask = safe_float(quote.get("total_ask") if quote.get("total_ask") is not None else quote.get("ask_size"))
        bid_ask_ratio = bid / ask if ask > 0 else (bid if bid > 0 else 1.0)
        raw_vwap = safe_float(quote.get("vwap"), 0.0)
        vwap_now = rolling_vwap if raw_vwap <= 0 or abs(raw_vwap - price) < 1e-9 else raw_vwap
        vwap_distance_pct = (price / vwap_now - 1) * 100 if vwap_now > 0 else 0.0
        bar_range = max(0.0, high_now - low_now)
        close_position_pct = ((price - low_now) / bar_range * 100.0) if bar_range > 0 else 50.0
        bar_return_pct = (price / open_now - 1) * 100.0 if open_now > 0 else 0.0
        bar_bull = price >= open_now
        higher_low = bool(len(recent_low_10) >= 6 and min(recent_low_10[-3:]) >= min(recent_low_10[-6:-3]))
        lower_high = bool(len(recent_high_10) >= 6 and max(recent_high_10[-3:]) <= max(recent_high_10[-6:-3]))
        compression_ready = bool(0 < range20_pct <= 3.2 and range5_pct <= max(1.2, range20_pct * 0.68))
        gentle_volume = bool(1.05 <= volume_ratio <= 1.65)
        aggressive_volume = bool(volume_ratio > 1.65)
        is_fake_breakout = bool(is_breakout and (price < vwap_now or bid_ask_ratio < 1.0))
        return {
            "ts": quote.get("ts"),
            "trade_date": quote.get("trade_date") or str(quote.get("ts", ""))[:10],
            "symbol": symbol,
            "price": price,
            "open": open_now,
            "vwap": vwap_now,
            "ema5": ema(prices, 5),
            "ema20": ema(prices, 20),
            "ema60": ema(prices, 60),
            "volume_now": volume_now,
            "volume_avg": volume_avg,
            "volume_ratio": volume_ratio,
            "range20_pct": range20_pct,
            "range5_pct": range5_pct,
            "momentum_3_pct": momentum_3_pct,
            "momentum_5_pct": momentum_5_pct,
            "recent_peak_pullback_pct": recent_peak_pullback_pct,
            "prev_high_20": prev_high,
            "prev_low_20": prev_low,
            "prev_high_10": prev_high_10,
            "prev_low_10": prev_low_10,
            "bid_ask_ratio": bid_ask_ratio,
            "vwap_distance_pct": vwap_distance_pct,
            "close_position_pct": close_position_pct,
            "bar_return_pct": bar_return_pct,
            "bar_bull": bar_bull,
            "higher_low": higher_low,
            "lower_high": lower_high,
            "compression_ready": compression_ready,
            "gentle_volume": gentle_volume,
            "aggressive_volume": aggressive_volume,
            "is_near_breakout": is_near_breakout,
            "is_breakout": is_breakout,
            "is_fake_breakout": is_fake_breakout,
        }


def v14_wave_scores(quote: Dict[str, Any], feat: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    price = safe_float(feat.get("price") or quote.get("price"))
    vwap_dist = safe_float(feat.get("vwap_distance_pct"), 0.0)
    bid_ask_ratio = safe_float(feat.get("bid_ask_ratio"), 1.0)
    mom3 = safe_float(feat.get("momentum_3_pct"), 0.0)
    mom5 = safe_float(feat.get("momentum_5_pct"), 0.0)
    close_pos = safe_float(feat.get("close_position_pct"), 50.0)
    vol = safe_float(feat.get("volume_ratio"), 1.0)
    peak_pullback = safe_float(feat.get("recent_peak_pullback_pct"), 0.0)
    higher_low = bool(feat.get("higher_low"))
    lower_high = bool(feat.get("lower_high"))
    minutes_open = minutes_after_market_open(quote.get("ts"), settings.get("market_open", "09:00"))
    long_score = 0.0
    short_score = 0.0
    long_reasons: List[str] = []
    short_reasons: List[str] = []

    high_pressure_reversal = bool(minutes_open >= 8 and vwap_dist >= 0.35 and bid_ask_ratio <= 0.62 and close_pos >= 62 and mom3 >= 0.05)
    if high_pressure_reversal:
        short_score += 44
        short_reasons.append(f"高檔假強勢轉空：VWAP {vwap_dist:.2f}% / 買賣比 {bid_ask_ratio:.2f} / 開盤後{minutes_open}分")
    if lower_high:
        short_score += 14
        short_reasons.append("高點下移")
    if -1.25 <= mom3 <= -0.05:
        short_score += 18
        short_reasons.append(f"3K 轉弱 {mom3:.2f}%")
    elif 0.05 <= mom3 <= 0.95 and bid_ask_ratio <= 0.62 and vwap_dist > 0:
        short_score += 12
        short_reasons.append("價格仍被拉高但賣壓未退")
    elif mom3 < -1.65:
        short_score -= 18
        short_reasons.append(f"已急殺 {mom3:.2f}%，不追空")
    if -1.8 <= mom5 <= -0.10:
        short_score += 10
        short_reasons.append(f"5K 空方延續 {mom5:.2f}%")
    elif mom5 < -2.6:
        short_score -= 12
        short_reasons.append("5K 跌幅過深，防反彈")
    if close_pos <= 45:
        short_score += 10
        short_reasons.append(f"位置偏低 {close_pos:.0f}%")
    if bid_ask_ratio <= 0.75:
        short_score += 16
        short_reasons.append(f"賣壓強於買盤 {bid_ask_ratio:.2f}")
    if vol >= 0.75:
        short_score += min(10.0, max(0.0, (vol - 0.75) * 8.0))
    if vwap_dist < -2.8:
        short_score -= 18
        short_reasons.append(f"離 VWAP 過遠 {vwap_dist:.2f}%")

    low_reversal = bool(vwap_dist <= -0.75 and mom3 >= 0.05 and close_pos >= 50 and bid_ask_ratio >= 0.70)
    if low_reversal:
        long_score += 36
        long_reasons.append(f"低檔轉強：VWAP {vwap_dist:.2f}% / 3K {mom3:.2f}%")
    if higher_low:
        long_score += 14
        long_reasons.append("低點墊高")
    if 0.05 <= mom3 <= 1.10:
        long_score += 16
        long_reasons.append(f"3K 轉強 {mom3:.2f}%")
    elif mom3 > 1.65:
        long_score -= 18
        long_reasons.append(f"已急拉 {mom3:.2f}%，不追多")
    if 0.10 <= mom5 <= 1.80:
        long_score += 8
    if close_pos >= 55:
        long_score += 10
        long_reasons.append(f"收盤位置轉強 {close_pos:.0f}%")
    if bid_ask_ratio >= 0.95:
        long_score += 12
        long_reasons.append(f"買盤回補 {bid_ask_ratio:.2f}")
    if vwap_dist >= 0.20 and bid_ask_ratio <= 0.70 and close_pos >= 60:
        long_score -= 42
        long_reasons.append("高檔賣壓厚，禁止追多")
    if minutes_open > 90 and not (vwap_dist <= -3.0 and mom3 >= 0.25 and bid_ask_ratio >= 0.90):
        long_score -= 34
        long_reasons.append("下跌日中段反彈，未達極端乖離轉強，不搶多")
    if vwap_dist > 2.4:
        long_score -= 18
        long_reasons.append(f"離 VWAP 過遠 {vwap_dist:.2f}%")
    if peak_pullback < -1.0 and mom3 < 0.25:
        long_score -= 10

    lot_size = safe_int(settings.get("lot_size"), 1000)
    fee_discount = safe_float(settings.get("fee_discount"), 1.0)
    tax_rate_pct = safe_float(settings.get("tax_rate_pct"), 0.15)
    cost_pct = compute_trade_cost(price, price, 1, lot_size, fee_discount, tax_rate_pct).get("cost_pct", 0.43)
    long_expected = max(0.0, (long_score - 58.0) / 14.0) - cost_pct
    short_expected = max(0.0, (short_score - 58.0) / 14.0) - cost_pct
    return {
        "long_score": round(max(0.0, min(100.0, long_score)), 2),
        "short_score": round(max(0.0, min(100.0, short_score)), 2),
        "long_expected_net_pct": round(long_expected, 3),
        "short_expected_net_pct": round(short_expected, 3),
        "long_reasons": long_reasons[:5],
        "short_reasons": short_reasons[:5],
        "minutes_open": minutes_open,
        "cost_pct": round(cost_pct, 3),
    }


def select_v14_candidate(quote: Dict[str, Any], feat: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    direction = str(settings.get("direction_code", "AUTO"))
    if direction == "REVERSE_TEST":
        return False, None
    w = v14_wave_scores(quote, feat, settings)
    min_score = safe_float(settings.get("v14_min_wave_score"), safe_float(settings.get("entry_score"), 68.0))
    min_ev = safe_float(settings.get("v14_min_expected_net_pct"), safe_float(settings.get("min_expected_net_pct"), 0.55))
    candidates: List[Dict[str, Any]] = []
    if direction in {"LONG_ONLY", "AUTO"} and w["long_score"] >= min_score and w["long_expected_net_pct"] >= min_ev:
        candidates.append({
            "side": "LONG", "action": "BUY", "rank": w["long_score"] + w["long_expected_net_pct"] * 10.0,
            "phase": "V14波段起點", "score": w["long_score"], "expected_net_pct": w["long_expected_net_pct"],
            "predicted_win_rate": min(95.0, 45.0 + w["long_score"] * 0.45),
            "reason": f"做多｜V14波段起點｜WaveScore {w['long_score']:.1f}｜預估淨利 {w['long_expected_net_pct']:.2f}%｜" + "、".join(w["long_reasons"]),
            "setup_type": "即時結構做多",
            "wave": w,
        })
    if direction in {"SHORT_ONLY", "AUTO"} and w["short_score"] >= min_score and w["short_expected_net_pct"] >= min_ev:
        candidates.append({
            "side": "SHORT", "action": "SELL", "rank": w["short_score"] + w["short_expected_net_pct"] * 10.0,
            "phase": "V14波段起點", "score": w["short_score"], "expected_net_pct": w["short_expected_net_pct"],
            "predicted_win_rate": min(95.0, 45.0 + w["short_score"] * 0.45),
            "reason": f"做空｜V14波段起點｜WaveScore {w['short_score']:.1f}｜預估淨利 {w['short_expected_net_pct']:.2f}%｜" + "、".join(w["short_reasons"]),
            "setup_type": "即時結構做空",
            "wave": w,
        })
    if not candidates:
        return False, None
    candidates.sort(key=lambda x: safe_float(x.get("rank"), 0.0), reverse=True)
    return True, candidates[0]


def wave_exit_ok(side: str, change_pct: float, feat: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[bool, str]:
    min_profit = safe_float(settings.get("v14_min_hold_profit_pct"), safe_float(settings.get("min_reversal_exit_gross_pct"), 0.65))
    profit_pct = change_pct if str(side).upper() == "LONG" else -change_pct
    if profit_pct < min_profit:
        return False, f"未達波段轉弱最低毛利 {min_profit:.2f}%"
    close_pos = safe_float(feat.get("close_position_pct"), 50.0)
    mom3 = safe_float(feat.get("momentum_3_pct"), 0.0)
    mom5 = safe_float(feat.get("momentum_5_pct"), 0.0)
    bid_ask_ratio = safe_float(feat.get("bid_ask_ratio"), 1.0)
    vwap_dist = safe_float(feat.get("vwap_distance_pct"), 0.0)
    if str(side).upper() == "LONG":
        wave_end = (close_pos <= 40 and mom3 <= -0.15) or mom3 <= -0.75 or bid_ask_ratio <= 0.62 or (vwap_dist > 1.2 and mom3 < 0.05)
        return wave_end, f"多方波段結束：位置{close_pos:.0f}% / 3K {mom3:.2f}% / 5K {mom5:.2f}% / 買賣比{bid_ask_ratio:.2f}"
    wave_end = (close_pos >= 60 and mom3 >= 0.15) or mom3 >= 0.75 or bid_ask_ratio >= 1.35 or (vwap_dist < -1.8 and mom3 > -0.05)
    return wave_end, f"空方波段結束：位置{close_pos:.0f}% / 3K {mom3:.2f}% / 5K {mom5:.2f}% / 買賣比{bid_ask_ratio:.2f}"


def default_settings(**overrides: Any) -> Dict[str, Any]:
    s = {
        "direction_code": "AUTO",
        "market_open": "09:00",
        "v14_wave_model": True,
        "v14_only_wave_model": True,
        "v14_min_wave_score": 68.0,
        "v14_min_expected_net_pct": 0.55,
        "v14_min_hold_profit_pct": 0.65,
        "max_holding_k": 45,
        "stop_loss_pct": 0.8,
        "take_profit_pct": 1.2,
        "cooldown_k": 4,
        "max_daily_trades": 8,
        "requested_trade_count": 80,
        "avoid_open_minutes": 5,
        "end_entry_minutes": 250,
        "scan_step_k": 1,
        "lot_size": 1000,
        "paper_lots": 1,
        "fee_discount": 1.0,
        "tax_rate_pct": 0.15,
        "allow_short": True,
        "allow_short_simulation": True,
    }
    s.update(overrides)
    return s


def _build_trade(trade_date: str, symbol: str, side: str, entry_time: str, entry_price: float, exit_time: str, exit_price: float, qty_lots: int, reason: str, settings: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    side = str(side).upper()
    lot_size = safe_int(settings.get("lot_size"), 1000)
    qty_shares = max(1, qty_lots) * max(1, lot_size)
    if side == "SHORT":
        gross_pct = (entry_price / exit_price - 1.0) * 100.0 if exit_price > 0 else 0.0
        gross_amount = (entry_price - exit_price) * qty_shares
        action = "SELL"
    else:
        gross_pct = (exit_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
        gross_amount = (exit_price - entry_price) * qty_shares
        action = "BUY"
    cost = compute_trade_cost(entry_price, exit_price, qty_lots, lot_size, safe_float(settings.get("fee_discount"), 1.0), safe_float(settings.get("tax_rate_pct"), 0.15))
    pnl_pct = gross_pct - cost["cost_pct"]
    pnl = gross_amount - cost["cost_amount"]
    row = {
        "date": trade_date,
        "action": action,
        "side": side,
        "entry_time": entry_time,
        "entry_price": round(entry_price, 3),
        "stop_loss": round(entry_price * (1 - settings.get("stop_loss_pct", 0.8)/100.0), 4) if side == "LONG" else round(entry_price * (1 + settings.get("stop_loss_pct", 0.8)/100.0), 4),
        "take_profit": round(entry_price * (1 + settings.get("take_profit_pct", 1.2)/100.0), 4) if side == "LONG" else round(entry_price * (1 - settings.get("take_profit_pct", 1.2)/100.0), 4),
        "exit_time": exit_time,
        "exit_price": round(exit_price, 3),
        "gross_pnl": round(gross_amount, 2),
        "gross_pnl_pct": round(gross_pct, 3),
        "cost_amount": cost["cost_amount"],
        "cost_pct": round(cost["cost_pct"], 3),
        "pnl_pct": round(pnl_pct, 3),
        "pnl": round(pnl),
        "result": "WIN" if pnl_pct > 0 else "LOSS",
        "exit_reason": reason,
        "lots": qty_lots,
        "qty_lots": qty_lots,
    }
    if extra:
        row.update(extra)
    return row


def run_v14_backtest_from_records(rows: List[Dict[str, Any]], settings: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run V14 real_quotes 1m backtest. Returns trades, summary, bars, signals."""
    settings = default_settings(**(settings or {}))
    bars = aggregate_real_quotes_to_1m(rows)
    features = FeatureBuilder()
    open_pos: Dict[str, Dict[str, Any]] = {}
    closed_trades: List[Dict[str, Any]] = []
    signals: List[Dict[str, Any]] = []
    k_index: Dict[str, int] = {}
    cooldown_until: Dict[str, int] = {}
    entries = 0
    last_bar: Dict[str, Dict[str, Any]] = {}
    requested = safe_int(settings.get("requested_trade_count"), 80)
    max_daily = safe_int(settings.get("max_daily_trades"), 8)
    qty_lots = max(1, safe_int(settings.get("paper_lots") or settings.get("lots"), 1))

    def can_open(symbol: str, idx: int) -> bool:
        if entries >= requested or entries >= max_daily:
            return False
        if idx < cooldown_until.get(symbol, -1):
            return False
        return True

    for row in bars:
        q = dict(row)
        symbol = str(q.get("symbol"))
        price = safe_float(q.get("price"))
        if price <= 0:
            continue
        k_index[symbol] = k_index.get(symbol, 0) + 1
        idx = k_index[symbol]
        last_bar[symbol] = q
        feat = features.update(q)
        ok, cand = select_v14_candidate(q, feat, settings)
        w = v14_wave_scores(q, feat, settings)
        sig = {
            "ts": q.get("ts"), "time": str(q.get("ts", ""))[11:16], "date": q.get("trade_date"),
            "symbol": symbol, "name": q.get("name", symbol), "price": price, "vwap": feat.get("vwap"),
            "action": cand.get("action") if (ok and cand) else "WAIT",
            "score": cand.get("score") if (ok and cand) else max(w["long_score"], w["short_score"]),
            "long_score": w["long_score"], "short_score": w["short_score"],
            "long_expected_net_pct": w["long_expected_net_pct"], "short_expected_net_pct": w["short_expected_net_pct"],
            "setup_type": cand.get("setup_type") if (ok and cand) else "觀望",
            "reason": cand.get("reason") if (ok and cand) else f"觀望 L{w['long_score']:.0f}/S{w['short_score']:.0f}",
        }
        sig.update({k: feat.get(k) for k in ["vwap_distance_pct", "bid_ask_ratio", "momentum_3_pct", "momentum_5_pct", "close_position_pct"]})
        signals.append(sig)

        pos = open_pos.get(symbol)
        if pos:
            side = str(pos.get("side", "LONG")).upper()
            raw_change = (price / safe_float(pos["entry_price"]) - 1.0) * 100.0 if safe_float(pos["entry_price"]) > 0 else 0.0
            hold_k = idx - safe_int(pos.get("entry_idx"), idx)
            exit_reason = ""
            if side == "SHORT":
                if raw_change >= settings["stop_loss_pct"]:
                    exit_reason = f"停損 {raw_change:.2f}%"
                elif raw_change <= -settings["take_profit_pct"]:
                    exit_reason = f"停利 {raw_change:.2f}%"
                elif hold_k >= settings["max_holding_k"]:
                    exit_reason = f"達最大持有 {settings['max_holding_k']}K"
                else:
                    ok_exit, why = wave_exit_ok("SHORT", raw_change, feat, settings)
                    if ok_exit:
                        exit_reason = why
            else:
                if raw_change <= -settings["stop_loss_pct"]:
                    exit_reason = f"停損 {raw_change:.2f}%"
                elif raw_change >= settings["take_profit_pct"]:
                    exit_reason = f"停利 {raw_change:.2f}%"
                elif hold_k >= settings["max_holding_k"]:
                    exit_reason = f"達最大持有 {settings['max_holding_k']}K"
                else:
                    ok_exit, why = wave_exit_ok("LONG", raw_change, feat, settings)
                    if ok_exit:
                        exit_reason = why
            if exit_reason:
                extra = {
                    "score": pos.get("score"), "predicted_win_rate": pos.get("predicted_win_rate"),
                    "setup_type": pos.get("setup_type"), "market_regime": "TREND_DOWN" if side == "SHORT" else "TREND_UP",
                    "reason": pos.get("reason"),
                }
                trade = _build_trade(str(q.get("trade_date")), symbol, side, pos["entry_time"], safe_float(pos["entry_price"]), q["ts"], price, qty_lots, exit_reason, settings, extra)
                closed_trades.append(trade)
                cooldown_until[symbol] = idx + safe_int(settings.get("cooldown_k"), 4)
                open_pos.pop(symbol, None)
                continue

        minutes_open = minutes_after_market_open(q.get("ts"), settings.get("market_open", "09:00"))
        if symbol not in open_pos and ok and cand and can_open(symbol, idx):
            if minutes_open < safe_int(settings.get("avoid_open_minutes"), 5):
                continue
            if minutes_open > safe_int(settings.get("end_entry_minutes"), 250):
                continue
            if cand.get("side") == "SHORT" and not (settings.get("allow_short", True) or settings.get("allow_short_simulation", True)):
                continue
            open_pos[symbol] = {
                "side": cand.get("side"), "entry_time": q.get("ts"), "entry_price": price, "entry_idx": idx,
                "reason": cand.get("reason"), "setup_type": cand.get("setup_type"), "score": cand.get("score"),
                "predicted_win_rate": cand.get("predicted_win_rate"),
            }
            entries += 1

    # force close remaining
    for symbol, pos in list(open_pos.items()):
        q = last_bar.get(symbol)
        if not q:
            continue
        extra = {"score": pos.get("score"), "predicted_win_rate": pos.get("predicted_win_rate"), "setup_type": pos.get("setup_type"), "reason": pos.get("reason"), "market_regime": "TREND_DOWN" if pos.get("side") == "SHORT" else "TREND_UP"}
        closed_trades.append(_build_trade(str(q.get("trade_date")), symbol, pos.get("side", "LONG"), pos["entry_time"], safe_float(pos["entry_price"]), q["ts"], safe_float(q["price"]), qty_lots, "收盤平倉", settings, extra))

    closed_trades_sorted = sorted(closed_trades, key=lambda t: str(t.get("exit_time") or t.get("entry_time") or ""), reverse=True)
    total_pnl = sum(safe_float(t.get("pnl")) for t in closed_trades)
    wins = sum(1 for t in closed_trades if safe_float(t.get("pnl_pct")) > 0)
    total = len(closed_trades)
    summary = {
        "bars": len(bars), "trades": total, "total_trades": total, "closed_trades": total,
        "wins": wins, "win_trades": wins, "lose_trades": total - wins,
        "win_rate": round((wins / total * 100.0) if total else 0.0, 1),
        "win_rate_ratio": round((wins / total) if total else 0.0, 4),
        "total_pnl": round(total_pnl),
        "total_pnl_pct": round(sum(safe_float(t.get("pnl_pct")) for t in closed_trades), 3),
        "avg_pnl": round(total_pnl / total, 2) if total else 0.0,
        "avg_pnl_pct": round(sum(safe_float(t.get("pnl_pct")) for t in closed_trades) / total, 3) if total else 0.0,
        "long_trades": sum(1 for t in closed_trades if t.get("side") == "LONG"),
        "short_trades": sum(1 for t in closed_trades if t.get("side") == "SHORT"),
        "source": "shared_v14_engine",
        "engine_version": "V14.4_SHARED_ENGINE",
        "settings": settings,
    }
    return closed_trades_sorted, summary, bars, signals


def run_v14_backtest_from_dataframe(df: Any, settings: Optional[Dict[str, Any]] = None) -> Tuple[Any, Dict[str, Any], Any, Any]:
    if pd is None:
        raise RuntimeError("pandas is required")
    norm = normalize_real_quotes_df(df)
    trades, summary, bars, signals = run_v14_backtest_from_records(norm.to_dict("records"), settings)
    return pd.DataFrame(trades), summary, pd.DataFrame(bars), pd.DataFrame(signals)
