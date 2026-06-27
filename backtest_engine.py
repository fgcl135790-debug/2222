import math
import requests
from datetime import datetime
from collections import defaultdict

from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from decision_engine import DecisionEngine
from multi_period_engine import MultiPeriodEngine


class BacktestEngine:
    BASE_URL = "https://api.fugle.tw/marketdata/v1.0/stock"

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(round(float(value)))
        except Exception:
            return default

    @staticmethod
    def _to_datetime(value):
        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None

    @staticmethod
    def fetch_historical_candles(
        api_key,
        symbol,
        timeframe="1",
    ):
        url = f"{BacktestEngine.BASE_URL}/historical/candles/{symbol}"

        headers = {
            "X-API-KEY": api_key,
        }

        params = {
            "timeframe": str(timeframe),
            "fields": "open,high,low,close,volume",
            "sort": "asc",
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20,
        )

        if response.status_code == 401:
            raise RuntimeError("API KEY 無效或權限不足。")

        if response.status_code == 429:
            raise RuntimeError("API 請求過多，稍後再試。")

        if response.status_code >= 400:
            raise RuntimeError(
                f"Fugle historical candles error: {response.status_code}"
            )

        payload = response.json()

        data = payload.get("data", [])

        candles = []

        for item in data:
            dt = BacktestEngine._to_datetime(item.get("date"))

            if dt is None:
                continue

            open_price = BacktestEngine._safe_float(item.get("open"))
            high_price = BacktestEngine._safe_float(item.get("high"))
            low_price = BacktestEngine._safe_float(item.get("low"))
            close_price = BacktestEngine._safe_float(item.get("close"))
            volume = BacktestEngine._safe_float(item.get("volume"))

            if close_price <= 0:
                continue

            candles.append(
                {
                    "time": dt,
                    "date": dt.date().isoformat(),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                }
            )

        candles = sorted(
            candles,
            key=lambda x: x["time"],
        )

        return candles

    @staticmethod
    def _group_by_day(candles):
        days = defaultdict(list)

        for candle in candles:
            days[candle["date"]].append(candle)

        return dict(days)

    @staticmethod
    def _build_series(candles):
        prices = []
        volumes = []
        vwaps = []
        times = []

        cum_amount = 0.0
        cum_volume = 0.0

        for c in candles:
            price = BacktestEngine._safe_float(c.get("close"))
            volume = BacktestEngine._safe_float(c.get("volume"))

            cum_amount += price * volume
            cum_volume += volume

            vwap = cum_amount / max(cum_volume, 1)

            prices.append(price)
            volumes.append(volume)
            vwaps.append(vwap)
            times.append(c.get("time"))

        return prices, volumes, vwaps, times

    @staticmethod
    def _make_decision(candles):
        prices, volumes, vwaps, times = BacktestEngine._build_series(candles)

        if len(prices) < 30:
            return None

        price = prices[-1]
        vwap = vwaps[-1]

        ema5 = MarketAnalyzer.calculate_ema(prices, 5)
        ema20 = MarketAnalyzer.calculate_ema(prices, 20)
        ema60 = MarketAnalyzer.calculate_ema(prices, 60)

        rsi = MarketAnalyzer.calculate_rsi(prices)
        macd, macd_signal, _ = MarketAnalyzer.calculate_macd(prices)
        momentum = MarketAnalyzer.momentum(prices)

        # 歷史 K 沒有五檔，所以回測先用中性買賣比
        bid_ratio = 1.0

        ai = AIPredictor.predict_trade(
            prices,
            volumes,
            ema5,
            ema20,
            ema60,
            rsi,
            macd,
            macd_signal,
            momentum,
            bid_ratio=bid_ratio,
            vwap=vwap,
        )

        decision = DecisionEngine.generate(
            ai=ai,
            price=price,
            vwap=vwap,
            ema5=ema5,
            ema20=ema20,
            ema60=ema60,
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            bid_ratio=bid_ratio,
            prices=prices,
            volumes=volumes,
        )

        multi_period = MultiPeriodEngine.analyze(
            prices=prices,
            volumes=volumes,
            vwap_values=vwaps,
            time_values=times,
        )

        decision = MultiPeriodEngine.apply_to_decision(
            decision=decision,
            multi_period=multi_period,
        )

        return decision

    @staticmethod
    def _simulate_exit(
        action,
        entry_price,
        entry_index,
        day_candles,
        decision,
        max_hold_bars=45,
    ):
        stop_loss = BacktestEngine._safe_float(
            decision.get("stop_loss"),
            0,
        )

        take_profit = BacktestEngine._safe_float(
            decision.get("take_profit"),
            0,
        )

        # 如果 decision 沒給合理停損停利，就用固定比例
        if action == "BUY":
            if stop_loss <= 0 or stop_loss >= entry_price:
                stop_loss = entry_price * 0.994

            if take_profit <= entry_price:
                take_profit = entry_price * 1.010

        elif action == "SELL":
            if stop_loss <= entry_price:
                stop_loss = entry_price * 1.006

            if take_profit <= 0 or take_profit >= entry_price:
                take_profit = entry_price * 0.990

        exit_price = entry_price
        exit_reason = "收盤"
        exit_index = min(
            len(day_candles) - 1,
            entry_index + max_hold_bars,
        )

        end_index = min(
            len(day_candles) - 1,
            entry_index + max_hold_bars,
        )

        for i in range(entry_index + 1, end_index + 1):
            c = day_candles[i]
            high = BacktestEngine._safe_float(c.get("high"))
            low = BacktestEngine._safe_float(c.get("low"))
            close = BacktestEngine._safe_float(c.get("close"))

            if action == "BUY":
                # 同一根同時碰停損停利時，保守視為先停損
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "停損"
                    exit_index = i
                    break

                if high >= take_profit:
                    exit_price = take_profit
                    exit_reason = "停利"
                    exit_index = i
                    break

            elif action == "SELL":
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "停損"
                    exit_index = i
                    break

                if low <= take_profit:
                    exit_price = take_profit
                    exit_reason = "停利"
                    exit_index = i
                    break

            exit_price = close
            exit_index = i

        if action == "BUY":
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        result = "WIN" if pnl_pct > 0 else "LOSS"

        if abs(pnl_pct) < 0.03:
            result = "FLAT"

        return {
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_index": exit_index,
            "pnl_pct": pnl_pct,
            "result": result,
        }

    @staticmethod
    def _summarize(trades):
        total = len(trades)

        wins = len([t for t in trades if t["result"] == "WIN"])
        losses = len([t for t in trades if t["result"] == "LOSS"])
        flats = len([t for t in trades if t["result"] == "FLAT"])

        win_rate = wins / total * 100 if total else 0

        total_pnl = sum(t["pnl_pct"] for t in trades)
        avg_pnl = total_pnl / total if total else 0

        gross_profit = sum(
            t["pnl_pct"]
            for t in trades
            if t["pnl_pct"] > 0
        )

        gross_loss = abs(
            sum(
                t["pnl_pct"]
                for t in trades
                if t["pnl_pct"] < 0
            )
        )

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else math.inf if gross_profit > 0 else 0
        )

        equity = 0
        peak = 0
        max_drawdown = 0

        max_consecutive_loss = 0
        current_loss_streak = 0

        for t in trades:
            equity += t["pnl_pct"]
            peak = max(peak, equity)
            drawdown = peak - equity
            max_drawdown = max(max_drawdown, drawdown)

            if t["result"] == "LOSS":
                current_loss_streak += 1
                max_consecutive_loss = max(
                    max_consecutive_loss,
                    current_loss_streak,
                )
            else:
                current_loss_streak = 0

        buy_trades = [t for t in trades if t["action"] == "BUY"]
        sell_trades = [t for t in trades if t["action"] == "SELL"]

        buy_wins = len([t for t in buy_trades if t["result"] == "WIN"])
        sell_wins = len([t for t in sell_trades if t["result"] == "WIN"])

        buy_win_rate = (
            buy_wins / len(buy_trades) * 100
            if buy_trades
            else 0
        )

        sell_win_rate = (
            sell_wins / len(sell_trades) * 100
            if sell_trades
            else 0
        )

        return {
            "total": total,
            "wins": wins,
            "losses": losses,
            "flats": flats,
            "win_rate": win_rate,
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "buy_win_rate": buy_win_rate,
            "sell_win_rate": sell_win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "max_consecutive_loss": max_consecutive_loss,
        }

    @staticmethod
    def run(
        api_key,
        symbol,
        timeframe="1",
        score_threshold=75,
        require_resonance=True,
        avoid_open_minutes=15,
        cooldown_bars=5,
        max_hold_bars=45,
    ):
        candles = BacktestEngine.fetch_historical_candles(
            api_key=api_key,
            symbol=symbol,
            timeframe=timeframe,
        )

        if not candles:
            return {
                "ok": False,
                "message": "沒有取得歷史 K 線資料。",
                "summary": {},
                "trades": [],
            }

        days = BacktestEngine._group_by_day(candles)

        trades = []

        for day, day_candles in days.items():
            if len(day_candles) < 60:
                continue

            i = max(30, avoid_open_minutes)

            while i < len(day_candles) - 2:
                current_candles = day_candles[: i + 1]

                decision = BacktestEngine._make_decision(current_candles)

                if not decision:
                    i += 1
                    continue

                action = decision.get("action", "WAIT")
                score = BacktestEngine._safe_int(decision.get("score", 0))
                multi_period = decision.get("multi_period", {}) or {}
                resonance = multi_period.get("resonance", "WAIT")
                multi_status = decision.get("multi_period_status", "盤整觀望")

                if action not in ["BUY", "SELL"]:
                    i += 1
                    continue

                if score < score_threshold:
                    i += 1
                    continue

                if require_resonance:
                    if action == "BUY" and resonance not in ["BULL", "BULL_STRONG"]:
                        i += 1
                        continue

                    if action == "SELL" and resonance not in ["BEAR", "BEAR_STRONG"]:
                        i += 1
                        continue

                entry_index = i + 1

                if entry_index >= len(day_candles):
                    break

                entry_candle = day_candles[entry_index]
                entry_price = BacktestEngine._safe_float(entry_candle["open"])

                if entry_price <= 0:
                    entry_price = BacktestEngine._safe_float(entry_candle["close"])

                exit_data = BacktestEngine._simulate_exit(
                    action=action,
                    entry_price=entry_price,
                    entry_index=entry_index,
                    day_candles=day_candles,
                    decision=decision,
                    max_hold_bars=max_hold_bars,
                )

                exit_index = exit_data["exit_index"]
                exit_candle = day_candles[exit_index]

                trades.append(
                    {
                        "date": day,
                        "action": action,
                        "score": score,
                        "multi_status": multi_status,
                        "resonance": resonance,
                        "entry_time": entry_candle["time"].strftime("%H:%M"),
                        "entry_price": round(entry_price, 2),
                        "exit_time": exit_candle["time"].strftime("%H:%M"),
                        "exit_price": round(exit_data["exit_price"], 2),
                        "exit_reason": exit_data["exit_reason"],
                        "pnl_pct": round(exit_data["pnl_pct"], 3),
                        "result": exit_data["result"],
                    }
                )

                i = exit_index + cooldown_bars

        summary = BacktestEngine._summarize(trades)

        return {
            "ok": True,
            "message": "回測完成",
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": len(candles),
            "days": len(days),
            "summary": summary,
            "trades": trades,
        }
