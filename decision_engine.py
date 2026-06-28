from intraday_label_engine import IntradayLabelEngine


class DecisionEngine:
    COST_PCT = 0.435
    DEFAULT_STOP_PCT = 0.6
    DEFAULT_TAKE_PCT = 1.8
    DEFAULT_MAX_HOLD_BARS = 25

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _base_wait(price, score, title, reason, extra=None):
        payload = {
            "action": "WAIT",
            "score": int(max(0, min(100, score))),
            "title": title,
            "reason": reason,
            "reasons": [reason],
            "entry_price": price,
            "stop_loss": 0,
            "take_profit": 0,
            "risk_reward": 0,
            "rebound": 50,
            "multi_period_status": "WAIT",
            "multi_period": {},
            "swing_state": "等待模型",
            "swing_prediction": {},
            "predicted_up_pct": 0,
            "predicted_down_pct": 0,
        }

        if extra:
            payload.update(extra)

        return payload

    @staticmethod
    def _build_trade_payload(
        action,
        price,
        score,
        prediction,
        model_package,
    ):
        stop_pct = float(model_package.get("stop_pct", DecisionEngine.DEFAULT_STOP_PCT))
        take_pct = float(model_package.get("take_pct", DecisionEngine.DEFAULT_TAKE_PCT))

        if action == "BUY":
            stop_loss = price * (1 - stop_pct / 100)
            take_profit = price * (1 + take_pct / 100)
            risk_reward = take_pct / stop_pct

            title = "模型預測做多"
            reason = (
                f"BUY 相似情境勝率 {prediction['buy']['win_rate']}%，"
                f"期望報酬 {prediction['buy']['expected_value']}%。"
            )

            reasons = [
                prediction["buy"].get("reason", ""),
                f"SELL 期望報酬 {prediction['sell']['expected_value']}%",
                f"BUY 樣本數 {prediction['buy']['sample_count']}",
                f"模型區間 {model_package.get('start_date')} ~ {model_package.get('end_date')}",
            ]

            multi_period_status = "BULL_STRONG"
            swing_state = "資料模型偏多"

        else:
            stop_loss = price * (1 + stop_pct / 100)
            take_profit = price * (1 - take_pct / 100)
            risk_reward = take_pct / stop_pct

            title = "模型預測做空"
            reason = (
                f"SELL 相似情境勝率 {prediction['sell']['win_rate']}%，"
                f"期望報酬 {prediction['sell']['expected_value']}%。"
            )

            reasons = [
                prediction["sell"].get("reason", ""),
                f"BUY 期望報酬 {prediction['buy']['expected_value']}%",
                f"SELL 樣本數 {prediction['sell']['sample_count']}",
                f"模型區間 {model_package.get('start_date')} ~ {model_package.get('end_date')}",
            ]

            multi_period_status = "BEAR_STRONG"
            swing_state = "資料模型偏空"

        return {
            "action": action,
            "score": int(max(0, min(100, score))),
            "title": title,
            "reason": reason,
            "reasons": reasons,
            "entry_price": price,
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "risk_reward": round(risk_reward, 2),
            "rebound": 55 if action == "BUY" else 45,
            "multi_period_status": multi_period_status,
            "multi_period": {},
            "swing_state": swing_state,
            "swing_prediction": prediction,
            "predicted_up_pct": take_pct if action == "BUY" else 0,
            "predicted_down_pct": take_pct if action == "SELL" else 0,
            "long_rr": round(risk_reward, 2),
            "short_rr": round(risk_reward, 2),
            "model_start_date": model_package.get("start_date", ""),
            "model_end_date": model_package.get("end_date", ""),
            "model_label_rows": model_package.get("label_rows", 0),
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
        ai = ai or {}
        price = DecisionEngine._safe_float(price)

        if price <= 0:
            return DecisionEngine._base_wait(
                price=price,
                score=0,
                title="價格異常",
                reason="目前價格小於等於 0，無法判斷。",
            )

        prices = prices or []
        volumes = volumes or []

        if len(prices) < 35:
            return DecisionEngine._base_wait(
                price=price,
                score=20,
                title="等待盤中資料",
                reason="至少需要 35 根盤中資料才能和近 30 日模型比對。",
            )

        model_package = ai.get("intraday_model_package")

        if not model_package:
            return DecisionEngine._base_wait(
                price=price,
                score=30,
                title="尚未建立股票模型",
                reason="請先讓系統抓取該股票近 30 日 K 線並建立當沖模型。",
            )

        model = model_package.get("model")

        if model is None:
            return DecisionEngine._base_wait(
                price=price,
                score=30,
                title="模型不存在",
                reason="該股票模型尚未正確建立。",
            )

        feature = IntradayLabelEngine.extract_current_features(
            prices=prices,
            volumes=volumes,
        )

        if feature is None:
            return DecisionEngine._base_wait(
                price=price,
                score=30,
                title="特徵不足",
                reason="目前盤中特徵不足，暫不進場。",
            )

        prediction = model.predict(
            feature=feature,
            min_expected_value=0.03,
            min_win_rate=43.0,
        )

        decision = prediction.get("decision", "WAIT")
        score = int(prediction.get("score", 50))

        buy = prediction.get("buy", {})
        sell = prediction.get("sell", {})

        if decision == "BUY":
            return DecisionEngine._build_trade_payload(
                action="BUY",
                price=price,
                score=score,
                prediction=prediction,
                model_package=model_package,
            )

        if decision == "SELL":
            return DecisionEngine._build_trade_payload(
                action="SELL",
                price=price,
                score=score,
                prediction=prediction,
                model_package=model_package,
            )

        wait_reasons = [
            f"BUY 勝率 {buy.get('win_rate', 0)}%，期望 {buy.get('expected_value', 0)}%",
            f"SELL 勝率 {sell.get('win_rate', 0)}%，期望 {sell.get('expected_value', 0)}%",
            f"BUY 樣本 {buy.get('sample_count', 0)} 筆",
            f"SELL 樣本 {sell.get('sample_count', 0)} 筆",
            f"模型區間 {model_package.get('start_date')} ~ {model_package.get('end_date')}",
        ]

        return DecisionEngine._base_wait(
            price=price,
            score=score,
            title="等待正期望訊號",
            reason="BUY / SELL 目前期望值尚未明顯為正。",
            extra={
                "reasons": wait_reasons,
                "swing_prediction": prediction,
                "model_start_date": model_package.get("start_date", ""),
                "model_end_date": model_package.get("end_date", ""),
                "model_label_rows": model_package.get("label_rows", 0),
            },
        )
