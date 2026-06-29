"""
Fugle WebSocket 即時行情引擎（v1.0 raw WebSocket）。

設計目標：
- 真實盤可用 WebSocket trades/books/candles 補強 REST。
- WebSocket 失敗時不讓主畫面掛掉，會自動退回 REST。
- 在 Streamlit rerun 下以背景 thread 保存最近逐筆成交與五檔變化。

官方 v1.0 WebSocket endpoint：
wss://api.fugle.tw/marketdata/v1.0/stock/streaming
"""

from __future__ import annotations

import json
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    websocket = None


WS_URL = "wss://api.fugle.tw/marketdata/v1.0/stock/streaming"


class _Safe:
    @staticmethod
    def f(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            x = float(value)
            if math.isnan(x) or math.isinf(x):
                return default
            return x
        except Exception:
            return default

    @staticmethod
    def i(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(round(float(value)))
        except Exception:
            return default


def _now_ts() -> float:
    return time.time()


def _norm_levels(levels: Any) -> List[Dict[str, float]]:
    if not isinstance(levels, list):
        return [{"price": 0.0, "size": 0.0} for _ in range(5)]
    result: List[Dict[str, float]] = []
    for item in levels[:5]:
        if isinstance(item, dict):
            result.append({"price": _Safe.f(item.get("price")), "size": _Safe.f(item.get("size"))})
    while len(result) < 5:
        result.append({"price": 0.0, "size": 0.0})
    return result


@dataclass
class _WSState:
    api_key_hash: str = ""
    symbol: str = ""
    enabled: bool = False
    connected: bool = False
    authenticated: bool = False
    last_event: str = ""
    last_error: str = ""
    last_message_ts: float = 0.0
    started_ts: float = 0.0
    subscribed: Dict[str, str] = field(default_factory=dict)
    latest_trade: Dict[str, Any] = field(default_factory=dict)
    latest_books: Dict[str, Any] = field(default_factory=dict)
    latest_candle: Dict[str, Any] = field(default_factory=dict)
    trades: deque = field(default_factory=lambda: deque(maxlen=400))
    books: deque = field(default_factory=lambda: deque(maxlen=120))
    raw_events: deque = field(default_factory=lambda: deque(maxlen=40))


_STATE = _WSState()
_LOCK = threading.RLock()
_WORKER: Optional["_FugleWSWorker"] = None


class _FugleWSWorker:
    def __init__(self, api_key: str, symbol: str, channels: Optional[List[str]] = None):
        self.api_key = str(api_key or "").strip()
        self.symbol = str(symbol or "").strip()
        self.channels = channels or ["trades", "books", "candles"]
        self.wsapp = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def start(self):
        if websocket is None:
            with _LOCK:
                _STATE.last_error = "缺少 websocket-client 套件，請確認 requirements.txt。"
                _STATE.enabled = False
            return

        self.thread = threading.Thread(target=self._run, name=f"fugle-ws-{self.symbol}", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        try:
            if self.wsapp is not None:
                self.wsapp.close()
        except Exception:
            pass

    def _run(self):
        with _LOCK:
            _STATE.started_ts = _now_ts()
            _STATE.connected = False
            _STATE.authenticated = False
            _STATE.last_error = ""
            _STATE.last_event = "connecting"
            _STATE.enabled = True

        try:
            self.wsapp = websocket.WebSocketApp(
                WS_URL,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self.wsapp.run_forever(ping_interval=20, ping_timeout=10, reconnect=0)
        except Exception as e:
            with _LOCK:
                _STATE.last_error = f"WebSocket 執行失敗：{type(e).__name__}: {e}"
                _STATE.connected = False
                _STATE.authenticated = False
                _STATE.last_event = "error"

    def _send(self, payload: Dict[str, Any]):
        try:
            if self.wsapp:
                self.wsapp.send(json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            with _LOCK:
                _STATE.last_error = f"WebSocket send 失敗：{type(e).__name__}: {e}"

    def _on_open(self, ws):
        with _LOCK:
            _STATE.connected = True
            _STATE.last_event = "connected"
            _STATE.last_message_ts = _now_ts()
        self._send({"event": "auth", "data": {"apikey": self.api_key}})

    def _on_close(self, ws, code, reason):
        with _LOCK:
            _STATE.connected = False
            _STATE.authenticated = False
            _STATE.last_event = "closed"
            if reason:
                _STATE.last_error = f"WebSocket closed: {code} {reason}"

    def _on_error(self, ws, error):
        with _LOCK:
            _STATE.last_error = f"WebSocket error: {error}"
            _STATE.last_event = "error"

    def _on_message(self, ws, message):
        try:
            payload = json.loads(message) if isinstance(message, str) else message
        except Exception:
            return

        event = payload.get("event")
        channel = payload.get("channel")
        data = payload.get("data") or {}
        ts = _now_ts()

        with _LOCK:
            _STATE.last_message_ts = ts
            _STATE.last_event = str(event or channel or "message")
            _STATE.raw_events.append({"ts": ts, "event": event, "channel": channel, "data": data})

        if event == "authenticated":
            with _LOCK:
                _STATE.authenticated = True
                _STATE.last_error = ""
            for ch in self.channels:
                self._send({"event": "subscribe", "data": {"channel": ch, "symbol": self.symbol}})
            return

        if event == "subscribed":
            with _LOCK:
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            _STATE.subscribed[str(item.get("channel"))] = str(item.get("id", ""))
                elif isinstance(data, dict):
                    _STATE.subscribed[str(data.get("channel"))] = str(data.get("id", ""))
            return

        if event == "error":
            with _LOCK:
                msg = data.get("message") if isinstance(data, dict) else str(payload)
                _STATE.last_error = str(msg or "WebSocket error")
            return

        if event == "heartbeat":
            return

        if event != "data" or not isinstance(data, dict):
            return

        sym = str(data.get("symbol") or "")
        if self.symbol and sym and sym != self.symbol:
            return

        if channel == "trades":
            self._handle_trade(data, ts)
        elif channel == "books":
            self._handle_books(data, ts)
        elif channel == "candles":
            with _LOCK:
                _STATE.latest_candle = dict(data)

    def _handle_trade(self, data: Dict[str, Any], ts: float):
        price = _Safe.f(data.get("price"))
        bid = _Safe.f(data.get("bid"))
        ask = _Safe.f(data.get("ask"))
        size = _Safe.f(data.get("size"))

        side = "NEUTRAL"
        if ask > 0 and price >= ask:
            side = "BUY"
        elif bid > 0 and price <= bid:
            side = "SELL"
        else:
            with _LOCK:
                prev = _Safe.f((_STATE.latest_trade or {}).get("price"))
            if prev > 0:
                if price > prev:
                    side = "BUY"
                elif price < prev:
                    side = "SELL"

        record = dict(data)
        record.update({"_ts": ts, "side": side, "price": price, "size": size, "bid": bid, "ask": ask})

        with _LOCK:
            _STATE.latest_trade = record
            _STATE.trades.append(record)

    def _handle_books(self, data: Dict[str, Any], ts: float):
        bids = _norm_levels(data.get("bids"))
        asks = _norm_levels(data.get("asks"))
        bid_depth = sum(x.get("size", 0) for x in bids)
        ask_depth = sum(x.get("size", 0) for x in asks)
        best_bid = bids[0]["price"] if bids else 0
        best_ask = asks[0]["price"] if asks else 0
        spread = max(best_ask - best_bid, 0) if best_bid and best_ask else 0
        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
        record = dict(data)
        record.update({
            "_ts": ts,
            "bids": bids,
            "asks": asks,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "spread_pct": (spread / mid * 100) if mid else 0,
        })
        with _LOCK:
            _STATE.latest_books = record
            _STATE.books.append(record)


class WebSocketLiveEngine:
    """Streamlit 用的 Fugle WebSocket 管理器。"""

    @staticmethod
    def _hash_key(api_key: str) -> str:
        s = str(api_key or "")
        if not s:
            return ""
        return f"len:{len(s)}|tail:{s[-4:]}"

    @staticmethod
    def reset(st=None):
        global _WORKER, _STATE
        if _WORKER is not None:
            _WORKER.stop()
        _WORKER = None
        with _LOCK:
            _STATE = _WSState()
        if st is not None:
            st.session_state["ws_live_status"] = {}

    @staticmethod
    def ensure_running(api_key: str, symbol: str, enabled: bool = True) -> Dict[str, Any]:
        global _WORKER, _STATE
        api_key = str(api_key or "").strip()
        symbol = str(symbol or "").strip()

        if not enabled:
            if _WORKER is not None:
                _WORKER.stop()
                _WORKER = None
            with _LOCK:
                _STATE.enabled = False
                _STATE.connected = False
                _STATE.authenticated = False
                _STATE.last_event = "disabled"
            return WebSocketLiveEngine.get_status()

        if not api_key or not symbol:
            return WebSocketLiveEngine.get_status()

        key_hash = WebSocketLiveEngine._hash_key(api_key)

        need_restart = False
        with _LOCK:
            if _WORKER is None:
                need_restart = True
            elif _STATE.symbol != symbol or _STATE.api_key_hash != key_hash:
                need_restart = True
            elif _STATE.last_event in ["closed", "error"] and (_now_ts() - _STATE.last_message_ts > 8):
                need_restart = True

        if need_restart:
            if _WORKER is not None:
                _WORKER.stop()
                time.sleep(0.2)
            with _LOCK:
                _STATE = _WSState(api_key_hash=key_hash, symbol=symbol, enabled=True)
            _WORKER = _FugleWSWorker(api_key=api_key, symbol=symbol)
            _WORKER.start()

        return WebSocketLiveEngine.get_status()

    @staticmethod
    def get_status() -> Dict[str, Any]:
        with _LOCK:
            age = (_now_ts() - _STATE.last_message_ts) if _STATE.last_message_ts else None
            return {
                "enabled": _STATE.enabled,
                "symbol": _STATE.symbol,
                "connected": _STATE.connected,
                "authenticated": _STATE.authenticated,
                "last_event": _STATE.last_event,
                "last_error": _STATE.last_error,
                "last_message_age_sec": round(age, 2) if age is not None else None,
                "subscribed": dict(_STATE.subscribed),
                "trade_count": len(_STATE.trades),
                "book_count": len(_STATE.books),
                "latest_trade": dict(_STATE.latest_trade),
                "latest_books": dict(_STATE.latest_books),
            }

    @staticmethod
    def apply_to_quote(quote: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """用 WebSocket 最新 trades/books 覆蓋 REST quote。沒有 WS 資料就原樣回傳。"""
        if not isinstance(quote, dict):
            quote = {}
        out = dict(quote)
        with _LOCK:
            lt = dict(_STATE.latest_trade)
            lb = dict(_STATE.latest_books)
            ok_symbol = (not symbol) or (not _STATE.symbol) or str(symbol) == str(_STATE.symbol)
            authenticated = _STATE.authenticated
        if not authenticated or not ok_symbol:
            return out

        if lt:
            p = _Safe.f(lt.get("price"))
            if p > 0:
                out["price"] = p
                out["last_size"] = _Safe.f(lt.get("size"), out.get("last_size", 0))
                out["trade"] = lt
                out["ws_price"] = p
                out["ws_trade"] = lt
        if lb:
            bids = _norm_levels(lb.get("bids"))
            asks = _norm_levels(lb.get("asks"))
            out["bids"] = bids
            out["asks"] = asks
            out["ws_books"] = lb
        if lt or lb:
            out["source_detail"] = "REST + WebSocket"
        return out

    @staticmethod
    def get_microstructure(symbol: str = "") -> Dict[str, Any]:
        """輸出可直接餵給 IntradaySignalEngine 的微結構欄位。"""
        with _LOCK:
            state = _STATE
            trades = list(state.trades)
            books = list(state.books)
            latest_trade = dict(state.latest_trade)
            latest_books = dict(state.latest_books)
            status = WebSocketLiveEngine.get_status()

        now = _now_ts()
        recent_trades = [t for t in trades if now - _Safe.f(t.get("_ts"), now) <= 60]
        recent_books = [b for b in books if now - _Safe.f(b.get("_ts"), now) <= 60]

        buy_vol = sum(_Safe.f(t.get("size")) for t in recent_trades if t.get("side") == "BUY")
        sell_vol = sum(_Safe.f(t.get("size")) for t in recent_trades if t.get("side") == "SELL")
        total_vol = buy_vol + sell_vol
        buy_pressure = 50.0 if total_vol <= 0 else 100.0 * buy_vol / total_vol
        sell_pressure = 50.0 if total_vol <= 0 else 100.0 * sell_vol / total_vol

        sizes = [_Safe.f(t.get("size")) for t in recent_trades if _Safe.f(t.get("size")) > 0]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        large_threshold = max(avg_size * 3.0, 100.0)
        large_buys = [t for t in recent_trades if t.get("side") == "BUY" and _Safe.f(t.get("size")) >= large_threshold]
        large_sells = [t for t in recent_trades if t.get("side") == "SELL" and _Safe.f(t.get("size")) >= large_threshold]

        bid_depth_slope = 0.0
        ask_depth_slope = 0.0
        fake_bid_wall_risk = 0.0
        fake_ask_wall_risk = 0.0
        spread_pct = _Safe.f(latest_books.get("spread_pct"))
        bid_depth = _Safe.f(latest_books.get("bid_depth"))
        ask_depth = _Safe.f(latest_books.get("ask_depth"))
        imbalance = 0.0
        if bid_depth + ask_depth > 0:
            imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) * 100

        if len(recent_books) >= 2:
            first = recent_books[0]
            last = recent_books[-1]
            secs = max(_Safe.f(last.get("_ts")) - _Safe.f(first.get("_ts")), 1)
            bid_depth_slope = (_Safe.f(last.get("bid_depth")) - _Safe.f(first.get("bid_depth"))) / secs
            ask_depth_slope = (_Safe.f(last.get("ask_depth")) - _Safe.f(first.get("ask_depth"))) / secs

            # 假牆近似：前一檔量很大，下一次明顯消失且沒有 trade-through。
            for prev, cur in zip(recent_books[:-1], recent_books[1:]):
                prev_bid0 = _Safe.f((prev.get("bids") or [{}])[0].get("size"))
                cur_bid0 = _Safe.f((cur.get("bids") or [{}])[0].get("size"))
                prev_ask0 = _Safe.f((prev.get("asks") or [{}])[0].get("size"))
                cur_ask0 = _Safe.f((cur.get("asks") or [{}])[0].get("size"))
                if prev_bid0 >= max(300, avg_size * 6) and cur_bid0 < prev_bid0 * 0.35:
                    fake_bid_wall_risk = max(fake_bid_wall_risk, min(100, (prev_bid0 - cur_bid0) / max(prev_bid0, 1) * 100))
                if prev_ask0 >= max(300, avg_size * 6) and cur_ask0 < prev_ask0 * 0.35:
                    fake_ask_wall_risk = max(fake_ask_wall_risk, min(100, (prev_ask0 - cur_ask0) / max(prev_ask0, 1) * 100))

        estimated_slippage_pct_buy = min(1.5, max(0.0, spread_pct * 0.5 + (0.12 if ask_depth < 500 and ask_depth > 0 else 0)))
        estimated_slippage_pct_sell = min(1.5, max(0.0, spread_pct * 0.5 + (0.12 if bid_depth < 500 and bid_depth > 0 else 0)))
        effective_cost_add_pct = max(estimated_slippage_pct_buy, estimated_slippage_pct_sell)

        execution_risk = "LOW"
        if spread_pct >= 0.25 or bid_depth + ask_depth < 1200:
            execution_risk = "MEDIUM"
        if spread_pct >= 0.6 or bid_depth + ask_depth < 500:
            execution_risk = "HIGH"

        reasons = []
        if total_vol > 0:
            if buy_pressure >= 62:
                reasons.append(f"WebSocket 主動買量偏強：{buy_pressure:.1f}%")
            elif sell_pressure >= 62:
                reasons.append(f"WebSocket 主動賣量偏強：{sell_pressure:.1f}%")
        if fake_bid_wall_risk >= 60:
            reasons.append("疑似假買牆：買一量快速消失")
        if fake_ask_wall_risk >= 60:
            reasons.append("疑似假賣牆：賣一量快速消失")
        if execution_risk != "LOW":
            reasons.append(f"WebSocket 估計成交風險：{execution_risk}")
        if large_buys:
            reasons.append(f"連續大買偵測：{len(large_buys)} 筆")
        if large_sells:
            reasons.append(f"連續大賣偵測：{len(large_sells)} 筆")

        available = bool(status.get("authenticated") and (recent_trades or recent_books))

        return {
            "available": available,
            "source": "websocket",
            "status": status,
            "buy_pressure": round(buy_pressure, 2),
            "sell_pressure": round(sell_pressure, 2),
            "net_aggressive_flow": round(buy_vol - sell_vol, 2),
            "trade_count_60s": len(recent_trades),
            "large_buy_count_60s": len(large_buys),
            "large_sell_count_60s": len(large_sells),
            "large_order_streak": max(len(large_buys), len(large_sells)),
            "bid_depth": round(bid_depth, 2),
            "ask_depth": round(ask_depth, 2),
            "bid_ask_imbalance": round(imbalance, 2),
            "bid_depth_slope": round(bid_depth_slope, 2),
            "ask_depth_slope": round(ask_depth_slope, 2),
            "fake_bid_wall_risk": round(fake_bid_wall_risk, 2),
            "fake_ask_wall_risk": round(fake_ask_wall_risk, 2),
            "estimated_slippage_pct_buy": round(estimated_slippage_pct_buy, 4),
            "estimated_slippage_pct_sell": round(estimated_slippage_pct_sell, 4),
            "effective_cost_add_pct": round(effective_cost_add_pct, 4),
            "execution_risk": execution_risk,
            "reasons": reasons[:6],
            "latest_trade": latest_trade,
            "latest_books": latest_books,
        }

    @staticmethod
    def render_sidebar_status(st, compact: bool = True):
        status = WebSocketLiveEngine.get_status()
        if not status.get("enabled"):
            st.caption("WebSocket：未啟用")
            return
        if status.get("authenticated"):
            age = status.get("last_message_age_sec")
            st.success(f"WebSocket 已連線｜{status.get('symbol')}｜延遲 {age}s")
        elif status.get("connected"):
            st.info("WebSocket 已連線，等待驗證 / 訂閱...")
        else:
            st.warning("WebSocket 尚未連線，已使用 REST 備援。")
        if status.get("last_error"):
            st.caption(f"WS 錯誤：{status.get('last_error')}")
