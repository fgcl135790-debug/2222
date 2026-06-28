from intraday_label_engine import IntradayLabelEngine


class DecisionEngine:
    """
    決策引擎 V7.5 修正版

    設計重點：
    1. 有建立「近 30 日當沖模型」時，優先使用模型判斷。
    2. 尚未建立模型時，不讓系統整個只剩 WAIT，而是回退到原本 AIPredictor 訊號。
    3. 回傳格式固定，避免 Header、回測、多週期、勝率統計讀不到欄位。
    """

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
    def _safe_int(value, default=0):
        try:
            if value is None:
                return default
            return int(round(float(value)))
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
            "swing_state": "等待確認",
            "swing_prediction": {},
            "predicted_up_pct": 0,
            "predicted_down_pct": 0,
            "long_rr": 0,
            "short_rr": 0,
        }

        if extra:
            payload.update(extra)

        return payload

    @staticmethod
    def _fallback_from_ai(ai, price, prices, volumes):
        """
        沒有建立近 30 日模型時，使用原本 AIPredictor 的 BUY / SELL / WAIT。
        這是為了避免：
        - 主畫面尚未建立模型時完全不動
        - 回測引擎沒有傳入模型時全部 0 筆交易
        """
        ai = ai or {}
        action = str(ai.get("signal", "WAIT") or "WAIT").upper()
        score = DecisionEngine._safe_int(ai.get("score", 0), 0)
        rebound = ai.get("rebound_prob", 50)
        reasons = ai.get("reasons") or ai.get("reason") or []

        if isinstance(reasons, str):
            reasons = [reasons]

        if not reasons:
            reasons = ["使用一般 AI 訊號，尚未套用近 30 日當沖模型。"]

        if len(prices or []) < 30:
            return DecisionEngine._base_wait(
                price=price,
                score=min(score, 35),
                title="等待盤中資料",
                reason="至少需要 30 根盤中資料才能做一般 AI 判斷。",
            )

        if action not in ["BUY", "SELL"]:
            return DecisionEngine._base_wait(
                price=price,
                score=score,
                title="一般 AI 觀望",
                reason="一般 AI 尚未出現明確多空訊號。",
                extra={
                    "reasons": reasons,
                    "rebound": rebound,
                },
            )

        # 太低分的舊 AI 訊號先不放行，避免亂槍打鳥。
        if score < 50:
            return DecisionEngine._base_wait(
                price=price,
                score=score,
                title="AI 分數不足",
                reason="一般 AI 有方向，但分數低於 50，暫不進場。",
                extra={
                    "reasons": reasons,
                    "rebound": rebound,
                },
            )

        stop_pct = DecisionEngine.DEFAULT_STOP_PCT
        take_pct = DecisionEngine.DEFAULT_TAKE_PCT

        if action == "BUY":
            stop_loss = price * (1 - stop_pct / 100)
            take_profit = price * (1 + take_pct / 100)
            title = "一般 AI 做多"
            reason = "尚未建立當沖模型，先使用一般 AI 多方訊號。"
            multi_period_status = "BULL_STRONG"
            predicted_up_pct = take_pct
            predicted_down_pct = 0
        else:
            stop_loss = price * (1 + stop_pct / 100)
            take_profit = price * (1 - take_pct / 100)
            title = "一般 AI 做空"
            reason = "尚未建立當沖模型，先使用一般 AI 空方訊號。"
            multi_period_status = "BEAR_STRONG"
            predicted_up_pct = 0
            predicted_down_pct = take_pct

        risk_reward = take_pct / max(stop_pct, 0.01)

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
            "rebound": rebound,
            "multi_period_status": multi_period_status,
            "multi_period": {},
            "swing_state": "一般 AI 備援模式",
            "swing_prediction": {
                "mode": "fallback_ai",
                "ai_signal": action,
                "ai_score": score,
                "note": "尚未建立近 30 日模型，或回測未傳入模型。",
            },
            "predicted_up_pct": predicted_up_pct,
            "predicted_down_pct": predicted_down_pct,
            "long_rr": round(risk_reward, 2),
            "short_rr": round(risk_reward, 2),
            "model_label_rows": 0,
        }

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
            risk_reward = take_pct / max(stop_pct, 0.01)

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
            predicted_up_pct = take_pct
            predicted_down_pct = 0

        else:
            stop_loss = price * (1 + stop_pct / 100)
            take_profit = price * (1 - take_pct / 100)
            risk_reward = take_pct / max(stop_pct, 0.01)

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
            predicted_up_pct = 0
            predicted_down_pct = take_pct

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
            "predicted_up_pct": predicted_up_pct,
            "predicted_down_pct": predicted_down_pct,
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

        model_package = ai.get("intraday_model_package")

        # 沒有模型時，回退到一般 AI，不再直接 WAIT。
        if not model_package:
            return DecisionEngine._fallback_from_ai(
                ai=ai,
                price=price,
                prices=prices,
                volumes=volumes,
            )

        model = model_package.get("model")

        if model is None:
            return DecisionEngine._fallback_from_ai(
                ai=ai,
                price=price,
                prices=prices,
                volumes=volumes,
            )

        if len(prices) < 35:
            return DecisionEngine._base_wait(
                price=price,
                score=30,
                title="等待盤中資料",
                reason="模型模式至少需要 35 根盤中資料才能比對相似情境。",
                extra={
                    "model_start_date": model_package.get("start_date", ""),
                    "model_end_date": model_package.get("end_date", ""),
                    "model_label_rows": model_package.get("label_rows", 0),
                },
            )

        feature = IntradayLabelEngine.extract_current_features(
            prices=prices,
            volumes=volumes,
        )

        if feature is None:
            return DecisionEngine._fallback_from_ai(
                ai=ai,
                price=price,
                prices=prices,
                volumes=volumes,
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
