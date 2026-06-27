try:
    from swing_prediction_engine import SwingPredictionEngine
except Exception:
    SwingPredictionEngine = None


class DecisionEngine:
    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _last(value, default=0.0):
        if isinstance(value, list):
            if not value:
                return default

            return DecisionEngine._safe_float(value[-1], default)

        return DecisionEngine._safe_float(value, default)

    @staticmethod
    def _base_decision(action, score, title, reason, price):
        return {
            "action": action,
            "score": int(score),
            "title": title,
            "reason": reason,
            "reasons": [reason],
            "entry_price": price,
            "stop_loss": 0,
            "take_profit": 0,
            "risk_reward": 0,
            "rebound": 50,
            "multi_period_status": "等待波段",
            "multi_period": {},
            "swing_prediction": {},
            "predicted_up_pct": 0,
            "predicted_down_pct": 0,
        }

    @staticmethod
    def generate(
        ai,
        price,
        vwap,
        ema5,
        ema20,
        ema60,
        rsi,
        macd,
        macd_signal,
        bid_ratio,
        prices,
        volumes,
    ):
        prices = prices or []
        volumes = volumes or []

        price = DecisionEngine._safe_float(price)
        vwap = DecisionEngine._safe_float(vwap, price)

        ai = ai or {}
        ai_signal = ai.get("signal", "WAIT")
        ai_score = int(DecisionEngine._safe_float(ai.get("score", 0), 0))

        if price <= 0 or len(prices) < 35:
            return DecisionEngine._base_decision(
                action="WAIT",
                score=35,
                title="等待資料",
                reason="資料不足，尚無法預測波段",
                price=price,
            )

        if SwingPredictionEngine is None:
            return DecisionEngine._base_decision(
                action="WAIT",
                score=35,
                title="預測引擎未載入",
                reason="swing_prediction_engine.py 尚未正確載入",
                price=price,
            )

        swing = SwingPredictionEngine.analyze(
            prices=prices,
            volumes=volumes,
            vwap=vwap,
            ema5=ema5,
            ema20=ema20,
            ema60=ema60,
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            bid_ratio=bid_ratio,
            cost_pct=0.435,
        )

        direction = swing.get("direction", "WAIT")
        swing_score = int(DecisionEngine._safe_float(swing.get("score", 0), 0))

        predicted_up_pct = DecisionEngine._safe_float(
            swing.get("predicted_up_pct"),
            0,
        )

        predicted_down_pct = DecisionEngine._safe_float(
            swing.get("predicted_down_pct"),
            0,
        )

        long_rr = DecisionEngine._safe_float(
            swing.get("long_rr"),
            0,
        )

        short_rr = DecisionEngine._safe_float(
            swing.get("short_rr"),
            0,
        )

        # =========================
        # AI 舊訊號只當加減分，不再作為唯一依據
        # =========================

        final_score = swing_score

        if direction == "BUY":
            if ai_signal == "BUY":
                final_score += 5

            elif ai_signal == "SELL":
                final_score -= 8

            final_score = max(0, min(100, final_score))

            stop_loss = DecisionEngine._safe_float(
                swing.get("long_stop"),
                price * 0.994,
            )

            take_profit = DecisionEngine._safe_float(
                swing.get("long_target"),
                price * 1.010,
            )

            risk = max(price - stop_loss, 0.01)
            reward = max(take_profit - price, 0)

            risk_reward = reward / risk if risk > 0 else 0

            if predicted_up_pct <= 0 or risk_reward < 1.05:
                return {
                    "action": "WAIT",
                    "score": min(final_score, 65),
                    "title": "多方空間不足",
                    "reason": "預估上漲空間或風險報酬不足",
                    "reasons": swing.get("reasons", []),
                    "entry_price": price,
                    "stop_loss": 0,
                    "take_profit": 0,
                    "risk_reward": round(risk_reward, 2),
                    "rebound": ai.get("rebound_prob", 50),
                    "multi_period_status": "等待波段",
                    "multi_period": {},
                    "swing_prediction": swing,
                    "predicted_up_pct": predicted_up_pct,
                    "predicted_down_pct": predicted_down_pct,
                }

            return {
                "action": "BUY",
                "score": int(final_score),
                "title": "波段預測做多",
                "reason": swing.get("reason", "預估上漲空間較佳"),
                "reasons": swing.get("reasons", []),
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round(risk_reward, 2),
                "rebound": ai.get("rebound_prob", 55),
                "multi_period_status": "BULL_STRONG",
                "swing_state": swing.get("state", "多方波段起點"),
                "multi_period": {},
                "swing_prediction": swing,
                "predicted_up_pct": predicted_up_pct,
                "predicted_down_pct": predicted_down_pct,
                "long_rr": long_rr,
                "short_rr": short_rr,
            }

        if direction == "SELL":
            if ai_signal == "SELL":
                final_score += 5

            elif ai_signal == "BUY":
                final_score -= 8

            final_score = max(0, min(100, final_score))

            stop_loss = DecisionEngine._safe_float(
                swing.get("short_stop"),
                price * 1.006,
            )

            take_profit = DecisionEngine._safe_float(
                swing.get("short_target"),
                price * 0.990,
            )

            risk = max(stop_loss - price, 0.01)
            reward = max(price - take_profit, 0)

            risk_reward = reward / risk if risk > 0 else 0

            if predicted_down_pct <= 0 or risk_reward < 1.05:
                return {
                    "action": "WAIT",
                    "score": min(final_score, 65),
                    "title": "空方空間不足",
                    "reason": "預估下跌空間或風險報酬不足",
                    "reasons": swing.get("reasons", []),
                    "entry_price": price,
                    "stop_loss": 0,
                    "take_profit": 0,
                    "risk_reward": round(risk_reward, 2),
                    "rebound": ai.get("rebound_prob", 50),
                    "multi_period_status": "等待波段",
                    "multi_period": {},
                    "swing_prediction": swing,
                    "predicted_up_pct": predicted_up_pct,
                    "predicted_down_pct": predicted_down_pct,
                }

            return {
                "action": "SELL",
                "score": int(final_score),
                "title": "波段預測做空",
                "reason": swing.get("reason", "預估下跌空間較佳"),
                "reasons": swing.get("reasons", []),
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round(risk_reward, 2),
                "rebound": ai.get("rebound_prob", 45),
                "multi_period_status": "BEAR_STRONG",
                "swing_state": swing.get("state", "空方波段起點"),
                "multi_period": {},
                "swing_prediction": swing,
                "predicted_up_pct": predicted_up_pct,
                "predicted_down_pct": predicted_down_pct,
                "long_rr": long_rr,
                "short_rr": short_rr,
            }

        return {
            "action": "WAIT",
            "score": min(swing_score, 70),
            "title": "等待波段",
            "reason": swing.get("reason", "目前沒有足夠波段優勢"),
            "reasons": swing.get("reasons", []),
            "entry_price": price,
            "stop_loss": 0,
            "take_profit": 0,
            "risk_reward": 0,
            "rebound": ai.get("rebound_prob", 50),
            "multi_period_status": "WAIT",
            "swing_state": swing.get("state", "等待波段"),
            "multi_period": {},
            "swing_prediction": swing,
            "predicted_up_pct": predicted_up_pct,
            "predicted_down_pct": predicted_down_pct,
            "long_rr": long_rr,
            "short_rr": short_rr,
        }
