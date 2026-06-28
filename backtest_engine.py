import math
import requests
from datetime import datetime
from collections import defaultdict

import pandas as pd

from market_analyzer import MarketAnalyzer
from ai_predictor import AIPredictor
from decision_engine import DecisionEngine
from multi_period_engine import MultiPeriodEngine

try:
    from stock_model_cache import StockModelCache
except Exception:
    StockModelCache = None


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
        headers = {"X-API-KEY": api_key}
        params = {
            "timeframe": str(timeframe),
            "fields": "open,high,low,close,volume",
            "sort": "asc",
        }

        response = requests.get(url, headers=headers, params=params, timeout=25)

        if response.status_code == 401:
            raise RuntimeError("API KEY 無效或權限不足。")
        if response.status_code == 429:
            raise RuntimeError("API 請求過多，請稍後再試。")
        if response.status_code >= 400:
            raise RuntimeError(f"Fugle historical candles error: {response.status_code}")

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

        return sorted(candles, key=lambda x: x["time"])

    @staticmethod
    def _candles_to_dataframe(candles):
        rows = []
        for c in candles:
            rows.append(
                {
                    "date": c.get("time"),
                    "open": c.get("open"),
                    "high": c.get("high"),
                    "low": c.get("low"),
                    "close": c.get("close"),
                    "volume": c.get("volume"),
                }
            )
        return pd.DataFrame(rows)

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
            if len(day_candles) >= 60:
                valid_days.append({"date": day, "candles": day_candles})

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
    def _make_decision(candles, model_package=None):
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

        if model_package is not None:
            ai["intraday_model_package"] = model_package

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

        # 成本感知模型的正期望訊號，不再被多週期共振直接改成 WAIT。
        # 多週期只作為參考欄位保留。
        model_signal_active = (
            decision.get("action") in ["BUY", "SELL"]
            and decision.get("model_label_rows", 0)
        )

        if model_signal_active:
            decision["multi_period"] = multi_period
            decision["multi_period_reference_status"] = multi_period.get("status", "")
            reasons = list(decision.get("reasons", []))
            reasons.insert(0, f"多週期參考：{multi_period.get('status', '未知')}｜模型以扣成本期望為主")
            decision["reasons"] = reasons[:8]
        else:
            decision = MultiPeriodEngine.apply_to_decision(decision=decision, multi_period=multi_period)

        return decision

    @staticmethod
    def _simulate_exit(
        action,
        entry_price,
        entry_index,
        day_candles,
        decision,
        max_hold_bars=50,
        default_stop_pct=0.6,
        default_take_pct=2.0,
        commission_rate_pct=0.1425,
        commission_discount=1.0,
        tax_rate_pct=0.15,
    ):
        default_stop_pct = BacktestEngine._safe_float(default_stop_pct, 0.6)
        default_take_pct = BacktestEngine._safe_float(default_take_pct, 2.0)
        commission_rate_pct = BacktestEngine._safe_float(commission_rate_pct, 0.1425)
        commission_discount = BacktestEngine._safe_float(commission_discount, 1.0)
        tax_rate_pct = BacktestEngine._safe_float(tax_rate_pct, 0.15)
        effective_commission_pct = commission_rate_pct * commission_discount

        stop_rate = default_stop_pct / 100
        take_rate = default_take_pct / 100

        if action == "BUY":
            stop_loss = entry_price * (1 - stop_rate)
            take_profit = entry_price * (1 + take_rate)
            stop_loss_pct = default_stop_pct
            take_profit_pct = default_take_pct
        elif action == "SELL":
            stop_loss = entry_price * (1 + stop_rate)
            take_profit = entry_price * (1 - take_rate)
            stop_loss_pct = default_stop_pct
            take_profit_pct = default_take_pct
        else:
            stop_loss = entry_price
            take_profit = entry_price
            stop_loss_pct = 0
            take_profit_pct = 0

        exit_price = entry_price
        exit_reason = "時間出場"
        exit_index = min(len(day_candles) - 1, entry_index + max_hold_bars)
        end_index = min(len(day_candles) - 1, entry_index + max_hold_bars)

        for i in range(entry_index + 1, end_index + 1):
            c = day_candles[i]
            high = BacktestEngine._safe_float(c.get("high"))
            low = BacktestEngine._safe_float(c.get("low"))
            close = BacktestEngine._safe_float(c.get("close"))

            if action == "BUY":
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
            gross_pnl_pct = (exit_price - entry_price) / entry_price * 100
            buy_commission_pct = effective_commission_pct
            sell_commission_pct = effective_commission_pct * (exit_price / entry_price)
            sell_tax_pct = tax_rate_pct * (exit_price / entry_price)
            cost_pct = buy_commission_pct + sell_commission_pct + sell_tax_pct
        else:
            gross_pnl_pct = (entry_price - exit_price) / entry_price * 100
            sell_commission_pct = effective_commission_pct
            sell_tax_pct = tax_rate_pct
            buyback_commission_pct = effective_commission_pct * (exit_price / entry_price)
            cost_pct = sell_commission_pct + sell_tax_pct + buyback_commission_pct

        net_pnl_pct = gross_pnl_pct - cost_pct
        result = "WIN" if net_pnl_pct > 0 else "LOSS"
        if abs(net_pnl_pct) < 0.03:
            result = "FLAT"

        hold_bars = max(0, exit_index - entry_index)

        return {
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_index": exit_index,
            "gross_pnl_pct": gross_pnl_pct,
            "cost_pct": cost_pct,
            "pnl_pct": net_pnl_pct,
            "result": result,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "commission_rate_pct": commission_rate_pct,
            "commission_discount": commission_discount,
            "effective_commission_pct": effective_commission_pct,
            "tax_rate_pct": tax_rate_pct,
            "hold_bars": hold_bars,
            "max_hold_bars": max_hold_bars,
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
        gross_total_pnl = sum(t.get("gross_pnl_pct", t.get("pnl_pct", 0)) for t in trades)
        total_cost_pct = sum(t.get("cost_pct", 0) for t in trades)

        gross_profit = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0)
        gross_loss = abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] < 0))

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
                max_consecutive_loss = max(max_consecutive_loss, current_loss_streak)
            else:
                current_loss_streak = 0

        buy_trades = [t for t in trades if t["action"] == "BUY"]
        sell_trades = [t for t in trades if t["action"] == "SELL"]
        buy_wins = len([t for t in buy_trades if t["result"] == "WIN"])
        sell_wins = len([t for t in sell_trades if t["result"] == "WIN"])
        buy_win_rate = buy_wins / len(buy_trades) * 100 if buy_trades else 0
        sell_win_rate = sell_wins / len(sell_trades) * 100 if sell_trades else 0

        predicted_ev_values = [t.get("predicted_expected_value") for t in trades if t.get("predicted_expected_value") is not None]
        avg_predicted_ev = sum(predicted_ev_values) / len(predicted_ev_values) if predicted_ev_values else 0

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
            "gross_total_pnl": gross_total_pnl,
            "total_cost_pct": total_cost_pct,
            "net_total_pnl": total_pnl,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "max_consecutive_loss": max_consecutive_loss,
            "avg_predicted_ev": avg_predicted_ev,
        }

    @staticmethod
    def _get_prediction_value(decision, path, default=None):
        cur = decision
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
        return cur

    @staticmethod
    def _flatten_day_items(day_items):
        out = []
        for item in day_items:
            out.extend(item.get("candles", []))
        return out

    @staticmethod
    def _build_model_package_from_candles(
        candles,
        symbol,
        timeframe,
        default_stop_pct,
        default_take_pct,
        max_hold_bars,
        estimated_cost_pct,
    ):
        if StockModelCache is None:
            return None, "StockModelCache 未載入，無法建立模型。"

        if not candles:
            return None, "訓練資料不足，無法建立模型。"

        try:
            model_package = StockModelCache.build_model_package(
                kline_df=BacktestEngine._candles_to_dataframe(candles),
                symbol=symbol,
                timeframe=timeframe,
                stop_pct=default_stop_pct,
                take_pct=default_take_pct,
                max_hold_bars=max_hold_bars,
                cost_pct=estimated_cost_pct,
            )

            label_rows = int(model_package.get("label_rows", 0) or 0)

            if label_rows <= 0:
                return None, "模型標籤數為 0，無法使用模型判斷。"

            return model_package, (
                f"模型區間 {model_package.get('start_date')} ~ {model_package.get('end_date')}，"
                f"標籤 {label_rows} 筆。"
            )

        except Exception as e:
            return None, f"模型建立失敗：{type(e).__name__}"

    @staticmethod
    def run(
        api_key,
        symbol,
        timeframe="1",
        score_threshold=60,
        require_resonance=False,
        avoid_open_minutes=15,
        cooldown_bars=5,
        max_hold_bars=50,
        day_scope="last_open_day",
        default_stop_pct=0.6,
        default_take_pct=2.0,
        commission_rate_pct=0.1425,
        commission_discount=1.0,
        tax_rate_pct=0.15,
        model_mode="walk_forward",
        walk_forward_train_days=5,
    ):
        """
        model_mode:
        - walk_forward：真實模式。測某一天時，只用該日以前的資料建立模型。
        - same_period：Debug 模式。用同一段資料建立模型再回測，會有資料洩漏。
        - classic：不使用近 30 日模型，只跑一般 AI 備援。
        """

        candles = BacktestEngine.fetch_historical_candles(
            api_key=api_key,
            symbol=symbol,
            timeframe=timeframe,
        )

        if not candles:
            return {"ok": False, "message": "沒有取得歷史 K 線資料。", "summary": {}, "trades": []}

        days = BacktestEngine._group_by_day(candles)
        selected_days = BacktestEngine._select_days(days=days, day_scope=day_scope)

        valid_days = []
        for day in sorted(days.keys()):
            day_candles = days[day]
            if len(day_candles) >= 60:
                valid_days.append({"date": day, "candles": day_candles})

        valid_day_index = {item["date"]: idx for idx, item in enumerate(valid_days)}

        if not selected_days:
            return {
                "ok": False,
                "message": "沒有找到足夠 K 線的開市日。",
                "summary": {},
                "trades": [],
                "candles": len(candles),
                "days": len(days),
            }

        try:
            timeframe_int = max(1, int(timeframe))
        except Exception:
            timeframe_int = 1

        avoid_bars = max(0, math.ceil(avoid_open_minutes / timeframe_int))
        walk_forward_train_days = max(1, BacktestEngine._safe_int(walk_forward_train_days, 5))

        effective_commission_pct = commission_rate_pct * commission_discount
        estimated_cost_pct = effective_commission_pct + effective_commission_pct + tax_rate_pct

        trades = []
        skipped_days = []
        day_model_messages = []

        shared_model_package = None
        shared_model_message = ""

        if model_mode == "same_period":
            shared_model_package, shared_model_message = BacktestEngine._build_model_package_from_candles(
                candles=candles,
                symbol=symbol,
                timeframe=timeframe,
                default_stop_pct=default_stop_pct,
                default_take_pct=default_take_pct,
                max_hold_bars=max_hold_bars,
                estimated_cost_pct=estimated_cost_pct,
            )
            shared_model_message = "同區間模型（有資料洩漏，只能 Debug）：" + shared_model_message

        elif model_mode == "classic":
            shared_model_message = "一般 AI 模式：未使用近 30 日相似 K 線模型。"

        else:
            model_mode = "walk_forward"
            shared_model_message = (
                f"Walk-forward 真實模式：每個測試日只用前 {walk_forward_train_days} 個交易日建模，"
                "不使用測試日與未來資料。"
            )

        for day_item in selected_days:
            day = day_item["date"]
            day_candles = day_item["candles"]

            if len(day_candles) < 60:
                continue

            model_package = None
            model_message = ""
            model_train_start = ""
            model_train_end = ""
            model_train_days = 0

            if model_mode == "same_period":
                model_package = shared_model_package
                model_message = shared_model_message
                if model_package:
                    model_train_start = model_package.get("start_date", "")
                    model_train_end = model_package.get("end_date", "")
                    model_train_days = int(model_package.get("trading_days", 0) or 0)

            elif model_mode == "classic":
                model_package = None
                model_message = shared_model_message

            else:
                idx = valid_day_index.get(day, -1)

                if idx <= 0:
                    skipped_days.append({"date": day, "reason": "沒有更早交易日可建模"})
                    continue

                train_start_idx = max(0, idx - walk_forward_train_days)
                train_day_items = valid_days[train_start_idx:idx]
                model_train_days = len(train_day_items)

                if model_train_days < max(3, min(walk_forward_train_days, 5)):
                    skipped_days.append({
                        "date": day,
                        "reason": f"訓練日不足：{model_train_days} 日",
                    })
                    continue

                train_candles = BacktestEngine._flatten_day_items(train_day_items)
                model_package, model_message = BacktestEngine._build_model_package_from_candles(
                    candles=train_candles,
                    symbol=symbol,
                    timeframe=timeframe,
                    default_stop_pct=default_stop_pct,
                    default_take_pct=default_take_pct,
                    max_hold_bars=max_hold_bars,
                    estimated_cost_pct=estimated_cost_pct,
                )

                model_train_start = train_day_items[0]["date"] if train_day_items else ""
                model_train_end = train_day_items[-1]["date"] if train_day_items else ""
                day_model_messages.append(f"{day}: {model_message}")

                if model_package is None:
                    skipped_days.append({"date": day, "reason": model_message})
                    continue

            i = max(35, avoid_bars)

            while i < len(day_candles) - 2:
                current_candles = day_candles[: i + 1]
                decision = BacktestEngine._make_decision(current_candles, model_package=model_package)

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
                    commission_rate_pct=commission_rate_pct,
                    commission_discount=commission_discount,
                    tax_rate_pct=tax_rate_pct,
                )

                exit_index = exit_data["exit_index"]
                exit_candle = day_candles[exit_index]
                swing_prediction = decision.get("swing_prediction", {}) or {}
                chosen = swing_prediction.get("chosen", {}) or {}
                buy_pred = swing_prediction.get("buy", {}) or {}
                sell_pred = swing_prediction.get("sell", {}) or {}

                trades.append(
                    {
                        "date": day,
                        "model_mode": model_mode,
                        "model_train_start": model_train_start,
                        "model_train_end": model_train_end,
                        "model_train_days": model_train_days,
                        "model_label_rows": model_package.get("label_rows", 0) if model_package else 0,
                        "action": action,
                        "score": score,
                        "multi_status": multi_status,
                        "resonance": resonance,
                        "entry_time": entry_candle["time"].strftime("%H:%M"),
                        "entry_price": round(entry_price, 2),
                        "stop_loss": round(exit_data["stop_loss"], 2),
                        "take_profit": round(exit_data["take_profit"], 2),
                        "stop_loss_pct": round(exit_data["stop_loss_pct"], 2),
                        "take_profit_pct": round(exit_data["take_profit_pct"], 2),
                        "exit_time": exit_candle["time"].strftime("%H:%M"),
                        "exit_price": round(exit_data["exit_price"], 2),
                        "exit_reason": exit_data["exit_reason"],
                        "hold_bars": exit_data["hold_bars"],
                        "max_hold_bars": exit_data["max_hold_bars"],
                        "gross_pnl_pct": round(exit_data["gross_pnl_pct"], 3),
                        "cost_pct": round(exit_data["cost_pct"], 3),
                        "pnl_pct": round(exit_data["pnl_pct"], 3),
                        "commission_rate_pct": round(exit_data["commission_rate_pct"], 4),
                        "commission_discount": round(exit_data["commission_discount"], 2),
                        "effective_commission_pct": round(exit_data["effective_commission_pct"], 4),
                        "tax_rate_pct": round(exit_data["tax_rate_pct"], 3),
                        "predicted_expected_value": chosen.get("expected_value"),
                        "predicted_win_rate": chosen.get("win_rate"),
                        "required_win_rate": swing_prediction.get("required_win_rate"),
                        "predicted_sample_count": chosen.get("sample_count"),
                        "buy_expected_value": buy_pred.get("expected_value"),
                        "sell_expected_value": sell_pred.get("expected_value"),
                        "buy_win_rate": buy_pred.get("win_rate"),
                        "sell_win_rate": sell_pred.get("win_rate"),
                        "risk_level": decision.get("risk_level"),
                        "result": exit_data["result"],
                    }
                )

                i = exit_index + cooldown_bars

        summary = BacktestEngine._summarize(trades)
        summary["skipped_days"] = len(skipped_days)
        summary["model_mode"] = model_mode
        selected_day_names = [d["date"] for d in selected_days]

        if model_mode == "same_period":
            leak_warning = "同區間模型有資料洩漏風險，不代表真實 AI 能力。"
        elif model_mode == "walk_forward":
            leak_warning = "Walk-forward：測試日只使用過去資料建模，較接近真實能力。"
        else:
            leak_warning = "一般 AI：未使用相似 K 線成本模型。"

        message = f"回測完成｜{leak_warning}｜{shared_model_message}"
        if not trades:
            message = f"回測完成，但沒有符合正期望條件的交易。｜{leak_warning}｜{shared_model_message}"

        return {
            "ok": True,
            "message": message,
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": len(candles),
            "all_days": len(days),
            "days": len(selected_days),
            "selected_days": selected_day_names,
            "model_mode": model_mode,
            "walk_forward_train_days": walk_forward_train_days,
            "leak_warning": leak_warning,
            "model_message": shared_model_message,
            "skipped_days": skipped_days,
            "day_model_messages": day_model_messages[-8:],
            "model_label_rows": shared_model_package.get("label_rows", 0) if shared_model_package else 0,
            "summary": summary,
            "trades": trades,
        }
