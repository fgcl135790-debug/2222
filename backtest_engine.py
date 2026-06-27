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
    def fetch_historical_candles(api_key, symbol, timeframe="1"):
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
            timeout=25,
        )

        if response.status_code == 401:
            raise RuntimeError("API KEY 無效或權限不足。")

        if response.status_code == 429:
            raise RuntimeError("API 請求過多，請稍後再試。")

        if response.status_code >= 400:
            raise RuntimeError(
                f"Fugle historical candles error: {response.status_code}"
            )

        payload = response.json()
        raw_data = payload.get("data", [])

        if not isinstance(raw_data, list):
            raise RuntimeError("Fugle 回傳格式異常：data 不是 list。")

        candles = []

        for item in raw_data:
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
    def _select_days(days, day_scope):
        valid_days = []

        for day in sorted(days.keys()):
            day_candles = days[day]

            # 太少 K 線通常不是完整交易日，先跳過
            if len(day_candles) >= 60:
                valid_days.append(
                    {
                        "date": day,
                        "candles": day_candles,
                    }
                )

        if not valid_days:
            return []

        if day_scope == "last_open_day":
            return [valid_days[-1]]

        if day_scope == "recent_5_days":
            return valid_days[-5:]

        return valid_days

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

        # 歷史 K 沒有五檔，回測先用中性值
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
        default_stop_pct=0.6,
        default_take_pct=1.0,
    ):
        stop_loss = BacktestEngine._safe_float(
            decision.get("stop_loss"),
            0,
        )

        take_profit = BacktestEngine._safe_float(
            decision.get("take_profit"),
            0,
        )

        default_stop_pct = BacktestEngine._safe_float(default_stop_pct, 0.6)
        default_take_pct = BacktestEngine._safe_float(default_take_pct, 1.0)

        stop_rate = default_stop_pct / 100
        take_rate = default_take_pct / 100

        # 如果 DecisionEngine 沒給合理停損停利，就用 UI 設定的固定百分比
        if action == "BUY":
            if stop_loss <= 0 or stop_loss >= entry_price:
                stop_loss = entry_price * (1 - stop_rate)

            if take_profit <= entry_price:
                take_profit = entry_price * (1 + take_rate)

            stop_loss_pct = (entry_price - stop_loss) / entry_price * 100
            take_profit_pct = (take_profit - entry_price) / entry_price * 100

        elif action == "SELL":
            if stop_loss <= entry_price:
                stop_loss = entry_price * (1 + stop_rate)

            if take_profit <= 0 or take_profit >= entry_price:
                take_profit = entry_price * (1 - take_rate)

            stop_loss_pct = (stop_loss - entry_price) / entry_price * 100
            take_profit_pct = (entry_price - take_profit) / entry_price * 100

        else:
            stop_loss_pct = 0
            take_profit_pct = 0

        exit_price = entry_price
        exit_reason = "時間出場"
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

        hold_bars = max(0, exit_index - entry_index)

        return {
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_index": exit_index,
            "pnl_pct": pnl_pct,
            "result": result,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "hold_bars": hold_bars,
            "max_hold_bars": max_hold_bars,
        }

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

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = 999
        else:
            profit_factor = 0

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
        day_scope="last_open_day",
        default_stop_pct=0.6,
        default_take_pct=1.0,
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
        selected_days = BacktestEngine._select_days(
            days=days,
            day_scope=day_scope,
        )

        if not selected_days:
            return {
                "ok": False,
                "message": "沒有找到足夠 K 線的開市日。",
                "summary": {},
                "trades": [],
                "candles": len(candles),
                "days": len(days),
            }

        trades = []

        try:
            timeframe_int = max(1, int(timeframe))
        except Exception:
            timeframe_int = 1

        avoid_bars = max(
            0,
            math.ceil(avoid_open_minutes / timeframe_int),
        )

        for day_item in selected_days:
            day = day_item["date"]
            day_candles = day_item["candles"]

            if len(day_candles) < 60:
                continue

            i = max(30, avoid_bars)

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
                    default_stop_pct=default_stop_pct,
                    default_take_pct=default_take_pct,
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
                        "stop_loss": round(exit_data["stop_loss"], 2),
                        "take_profit": round(exit_data["take_profit"], 2),
                        "stop_loss_pct": round(exit_data["stop_loss_pct"], 2),
                        "take_profit_pct": round(exit_data["take_profit_pct"], 2),
                        "hold_bars": exit_data["hold_bars"],
                        "max_hold_bars": exit_data["max_hold_bars"],
                    }
                )

                i = exit_index + cooldown_bars

        summary = BacktestEngine._summarize(trades)
        selected_day_names = [d["date"] for d in selected_days]

        message = "回測完成"

        if not trades:
            message = "回測完成，但沒有符合條件的交易。可以降低 Score 或取消多週期共振。"

        return {
            "ok": True,
            "message": message,
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": len(candles),
            "all_days": len(days),
            "days": len(selected_days),
            "selected_days": selected_day_names,
            "summary": summary,
            "trades": trades,
        }
