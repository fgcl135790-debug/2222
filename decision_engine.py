class DecisionEngine:
    """
    V8 Swing Forecast Decision Engine
    目的：不再用「條件符合」當作買賣，而是估算未來波段上漲/下跌空間。
    回傳格式維持和原本系統相容。
    """

    COST_PCT = 0.435  # 手續費 0.1425%*2 + 當沖稅 0.15% 的大約值

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _series(value):
        if value is None:
            return []

        if isinstance(value, list):
            return [DecisionEngine._safe_float(v) for v in value]

        try:
            if hasattr(value, "tolist"):
                return [DecisionEngine._safe_float(v) for v in value.tolist()]
        except Exception:
            pass

        return [DecisionEngine._safe_float(value)]

    @staticmethod
    def _last(value, default=0.0):
        data = DecisionEngine._series(value)
        if not data:
            return default
        return data[-1]

    @staticmethod
    def _ema(values, span):
        data = DecisionEngine._series(values)
        if not data:
            return []

        alpha = 2 / (span + 1)
        result = [data[0]]

        for price in data[1:]:
            result.append(price * alpha + result[-1] * (1 - alpha))

        return result

    @staticmethod
    def _avg(values, n=20):
        data = DecisionEngine._series(values)
        data = data[-n:]
        if not data:
            return 0.0
        return sum(data) / len(data)

    @staticmethod
    def _slope_pct(values, n=10):
        data = DecisionEngine._series(values)
        if len(data) < n + 1:
            return 0.0

        start = data[-n - 1]
        end = data[-1]

        if start <= 0:
            return 0.0

        return (end - start) / start * 100

    @staticmethod
    def _recent_high(values, n=30):
        data = DecisionEngine._series(values)
        if not data:
            return 0.0
        return max(data[-n:])

    @staticmethod
    def _recent_low(values, n=30):
        data = DecisionEngine._series(values)
        if not data:
            return 0.0
        return min(data[-n:])

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def _rsi_from_prices(prices, n=14):
        data = DecisionEngine._series(prices)
        if len(data) < n + 2:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(data)):
            diff = data[i] - data[i - 1]
            gains.append(max(diff, 0))
            losses.append(abs(min(diff, 0)))

        avg_gain = sum(gains[-n:]) / n
        avg_loss = sum(losses[-n:]) / n

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _rsi_slope_from_prices(prices, n=14):
        data = DecisionEngine._series(prices)
        if len(data) < n + 6:
            return 0.0

        now = DecisionEngine._rsi_from_prices(data, n)
        prev = DecisionEngine._rsi_from_prices(data[:-4], n)
        return now - prev

    @staticmethod
    def _macd_from_prices(prices):
        data = DecisionEngine._series(prices)
        if len(data) < 30:
            return 0.0, 0.0, 0.0, 0.0

        ema12 = DecisionEngine._ema(data, 12)
        ema26 = DecisionEngine._ema(data, 26)
        macd_line = []

        for a, b in zip(ema12, ema26):
            macd_line.append(a - b)

        signal = DecisionEngine._ema(macd_line, 9)
        hist = macd_line[-1] - signal[-1]

        if len(macd_line) >= 5 and len(signal) >= 5:
            prev_hist = macd_line[-4] - signal[-4]
            hist_accel = hist - prev_hist
        else:
            hist_accel = 0.0

        return macd_line[-1], signal[-1], hist, hist_accel

    @staticmethod
    def _atr_close_pct(prices, n=20):
        data = DecisionEngine._series(prices)
        if len(data) < 3:
            return 0.10

        moves = []
        for i in range(1, len(data)):
            prev = data[i - 1]
            now = data[i]
            if prev > 0:
                moves.append(abs(now - prev) / prev * 100)

        recent = moves[-n:]
        if not recent:
            return 0.10

        return sum(recent) / len(recent)

    @staticmethod
    def _base_wait(price, score, title, reason, extra=None):
        payload = {
            "action": "WAIT",
            "score": int(DecisionEngine._clamp(score, 0, 100)),
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
            "swing_prediction": {},
            "predicted_up_pct": 0,
            "predicted_down_pct": 0,
        }

        if extra:
            payload.update(extra)

        return payload

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
        prices = DecisionEngine._series(prices)
        volumes = DecisionEngine._series(volumes)

        price = DecisionEngine._safe_float(price)

        if price <= 0:
            return DecisionEngine._base_wait(
                price=price,
                score=0,
                title="價格資料異常",
                reason="目前價格小於等於 0，無法判斷。",
            )

        if len(prices) < 35:
            return DecisionEngine._base_wait(
                price=price,
                score=20,
                title="等待資料",
                reason="至少需要 35 根 K 才能估算波段。",
            )

        if not volumes:
            volumes = [1 for _ in prices]

        calc_ema5 = DecisionEngine._ema(prices, 5)
        calc_ema20 = DecisionEngine._ema(prices, 20)
        calc_ema60 = DecisionEngine._ema(prices, 60)

        ema5_v = DecisionEngine._last(ema5, calc_ema5[-1])
        ema20_v = DecisionEngine._last(ema20, calc_ema20[-1])
        ema60_v = DecisionEngine._last(ema60, calc_ema60[-1])

        if ema5_v <= 0:
            ema5_v = calc_ema5[-1]
        if ema20_v <= 0:
            ema20_v = calc_ema20[-1]
        if ema60_v <= 0:
            ema60_v = calc_ema60[-1]

        vwap_v = DecisionEngine._safe_float(vwap, price)
        if vwap_v <= 0:
            vwap_v = price

        input_rsi = DecisionEngine._last(rsi, None)
        if input_rsi is None or input_rsi <= 0:
            rsi_v = DecisionEngine._rsi_from_prices(prices)
        else:
            rsi_v = input_rsi

        rsi_slope = DecisionEngine._rsi_slope_from_prices(prices)

        calc_macd, calc_signal, calc_hist, calc_hist_accel = DecisionEngine._macd_from_prices(prices)

        macd_v = DecisionEngine._last(macd, calc_macd)
        signal_v = DecisionEngine._last(macd_signal, calc_signal)
        macd_hist = macd_v - signal_v

        if abs(macd_v) < 0.000001 and abs(signal_v) < 0.000001:
            macd_v = calc_macd
            signal_v = calc_signal
            macd_hist = calc_hist
            macd_hist_accel = calc_hist_accel
        else:
            macd_hist_accel = calc_hist_accel

        bid_ratio = DecisionEngine._safe_float(bid_ratio, 1.0)

        avg_volume_20 = DecisionEngine._avg(volumes, 20)
        now_volume = volumes[-1] if volumes else 0
        volume_ratio = now_volume / max(avg_volume_20, 1)

        slope_3 = DecisionEngine._slope_pct(prices, 3)
        slope_5 = DecisionEngine._slope_pct(prices, 5)
        slope_10 = DecisionEngine._slope_pct(prices, 10)
        slope_20 = DecisionEngine._slope_pct(prices, 20)

        prev_slope_5 = 0.0
        if len(prices) >= 11:
            prev_slope_5 = DecisionEngine._slope_pct(prices[:-5], 5)

        ema_gap = 0.0
        if ema20_v > 0:
            ema_gap = (ema5_v - ema20_v) / ema20_v * 100

        vwap_gap = 0.0
        if vwap_v > 0:
            vwap_gap = (price - vwap_v) / vwap_v * 100

        high_30 = DecisionEngine._recent_high(prices, 30)
        low_30 = DecisionEngine._recent_low(prices, 30)
        high_60 = DecisionEngine._recent_high(prices, 60)
        low_60 = DecisionEngine._recent_low(prices, 60)

        distance_to_high_30 = 0.0
        distance_to_low_30 = 0.0
        distance_to_high_60 = 0.0
        distance_to_low_60 = 0.0
        range_60_pct = 0.0

        if price > 0:
            distance_to_high_30 = (high_30 - price) / price * 100
            distance_to_low_30 = (price - low_30) / price * 100
            distance_to_high_60 = (high_60 - price) / price * 100
            distance_to_low_60 = (price - low_60) / price * 100
            range_60_pct = (high_60 - low_60) / price * 100

        atr_pct = DecisionEngine._atr_close_pct(prices, 20)

        projected_base = max(
            atr_pct * 6.5,
            range_60_pct * 0.35,
            0.35,
        )

        long_score = 0
        long_reasons = []

        if price >= vwap_v:
            long_score += 8
            long_reasons.append("價格在 VWAP 上方")
        elif -0.25 <= vwap_gap < 0:
            long_score += 5
            long_reasons.append("價格接近 VWAP 下方，可能準備站回")

        if -0.15 <= vwap_gap <= 0.80:
            long_score += 8
            long_reasons.append("多方沒有明顯追高")

        if ema5_v >= ema20_v:
            long_score += 9
            long_reasons.append("EMA5 不弱於 EMA20")

        if ema20_v >= ema60_v:
            long_score += 5
            long_reasons.append("EMA20 不弱於 EMA60")

        if slope_3 > 0:
            long_score += 11
            long_reasons.append("3K 短線轉強")

        if slope_10 > 0:
            long_score += 8
            long_reasons.append("10K 波段向上")

        if prev_slope_5 <= 0 and slope_5 > 0:
            long_score += 12
            long_reasons.append("剛出現由弱轉強")

        if macd_hist > 0:
            long_score += 8
            long_reasons.append("MACD Hist 偏多")

        if macd_hist_accel > 0:
            long_score += 7
            long_reasons.append("MACD 動能增強")

        if 40 <= rsi_v <= 68:
            long_score += 8
            long_reasons.append("RSI 未過熱")

        if rsi_slope > 0:
            long_score += 5
            long_reasons.append("RSI 正在轉強")

        if volume_ratio >= 0.75:
            long_score += 5
            long_reasons.append("量能沒有過低")

        if volume_ratio >= 1.15:
            long_score += 5
            long_reasons.append("量能放大")

        if distance_to_high_30 >= 0.20:
            long_score += 6
            long_reasons.append("距離短線高點仍有空間")

        if distance_to_high_60 >= 0.35:
            long_score += 5
            long_reasons.append("距離 60K 高點仍有空間")

        if bid_ratio >= 1.03:
            long_score += 3
            long_reasons.append("委買略優")

        if vwap_gap > 1.10:
            long_score -= 15
            long_reasons.append("離 VWAP 過遠，扣分")

        if distance_to_high_30 < 0.12 and rsi_v >= 62:
            long_score -= 14
            long_reasons.append("接近短線高點，扣分")

        if rsi_v >= 73:
            long_score -= 18
            long_reasons.append("RSI 過熱，扣分")

        short_score = 0
        short_reasons = []

        if price <= vwap_v:
            short_score += 8
            short_reasons.append("價格在 VWAP 下方")
        elif 0 < vwap_gap <= 0.25:
            short_score += 5
            short_reasons.append("價格接近 VWAP 上方，可能反彈失敗")

        if -0.80 <= vwap_gap <= 0.15:
            short_score += 8
            short_reasons.append("空方沒有明顯追空")

        if ema5_v <= ema20_v:
            short_score += 9
            short_reasons.append("EMA5 不強於 EMA20")

        if ema20_v <= ema60_v:
            short_score += 5
            short_reasons.append("EMA20 不強於 EMA60")

        if slope_3 < 0:
            short_score += 11
            short_reasons.append("3K 短線轉弱")

        if slope_10 < 0:
            short_score += 8
            short_reasons.append("10K 波段向下")

        if prev_slope_5 >= 0 and slope_5 < 0:
            short_score += 12
            short_reasons.append("剛出現由強轉弱")

        if macd_hist < 0:
            short_score += 8
            short_reasons.append("MACD Hist 偏空")

        if macd_hist_accel < 0:
            short_score += 7
            short_reasons.append("MACD 動能轉弱")

        if 32 <= rsi_v <= 60:
            short_score += 8
            short_reasons.append("RSI 未過低")

        if rsi_slope < 0:
            short_score += 5
            short_reasons.append("RSI 正在轉弱")

        if volume_ratio >= 0.75:
            short_score += 5
            short_reasons.append("量能沒有過低")

        if volume_ratio >= 1.15:
            short_score += 5
            short_reasons.append("量能放大")

        if distance_to_low_30 >= 0.20:
            short_score += 6
            short_reasons.append("距離短線低點仍有空間")

        if distance_to_low_60 >= 0.35:
            short_score += 5
            short_reasons.append("距離 60K 低點仍有空間")

        if bid_ratio <= 0.97:
            short_score += 3
            short_reasons.append("委賣略優")

        if vwap_gap < -1.10:
            short_score -= 15
            short_reasons.append("離 VWAP 過遠，扣分")

        if distance_to_low_30 < 0.12 and rsi_v <= 38:
            short_score -= 14
            short_reasons.append("接近短線低點，扣分")

        if rsi_v <= 25:
            short_score -= 18
            short_reasons.append("RSI 過低，扣分")

        long_score = int(DecisionEngine._clamp(long_score, 0, 100))
        short_score = int(DecisionEngine._clamp(short_score, 0, 100))

        long_momentum = max(slope_3, 0) * 0.35 + max(slope_10, 0) * 0.25
        short_momentum = abs(min(slope_3, 0)) * 0.35 + abs(min(slope_10, 0)) * 0.25

        if macd_hist > 0:
            long_momentum += 0.12
        if macd_hist_accel > 0:
            long_momentum += 0.10
        if volume_ratio >= 1.15:
            long_momentum += 0.12

        if macd_hist < 0:
            short_momentum += 0.12
        if macd_hist_accel < 0:
            short_momentum += 0.10
        if volume_ratio >= 1.15:
            short_momentum += 0.12

        predicted_up_pct = projected_base * (0.65 + long_score / 120) + long_momentum
        predicted_down_pct = projected_base * (0.65 + short_score / 120) + short_momentum

        if distance_to_high_60 > 0:
            predicted_up_pct = min(predicted_up_pct, distance_to_high_60 + projected_base * 0.4)

        if distance_to_low_60 > 0:
            predicted_down_pct = min(predicted_down_pct, distance_to_low_60 + projected_base * 0.4)

        predicted_up_pct = DecisionEngine._clamp(predicted_up_pct, 0.15, 4.5)
        predicted_down_pct = DecisionEngine._clamp(predicted_down_pct, 0.15, 4.5)

        long_risk_pct = DecisionEngine._clamp(max(0.35, atr_pct * 4.0), 0.35, 1.20)
        short_risk_pct = DecisionEngine._clamp(max(0.35, atr_pct * 4.0), 0.35, 1.20)

        long_rr = predicted_up_pct / max(long_risk_pct, 0.01)
        short_rr = predicted_down_pct / max(short_risk_pct, 0.01)

        ai_signal = ai.get("signal", "WAIT")
        ai_score = int(DecisionEngine._safe_float(ai.get("score", 0), 0))

        if ai_signal == "BUY":
            long_score = min(100, long_score + 4)
        elif ai_signal == "SELL":
            short_score = min(100, short_score + 4)

        long_edge = long_score + predicted_up_pct * 9 + long_rr * 5
        short_edge = short_score + predicted_down_pct * 9 + short_rr * 5

        swing_prediction = {
            "price": round(price, 2),
            "vwap": round(vwap_v, 2),
            "vwap_gap": round(vwap_gap, 3),
            "ema_gap": round(ema_gap, 3),
            "rsi": round(rsi_v, 2),
            "rsi_slope": round(rsi_slope, 3),
            "macd_hist": round(macd_hist, 5),
            "macd_hist_accel": round(macd_hist_accel, 5),
            "volume_ratio": round(volume_ratio, 2),
            "slope_3": round(slope_3, 3),
            "slope_10": round(slope_10, 3),
            "slope_20": round(slope_20, 3),
            "atr_pct": round(atr_pct, 3),
            "range_60_pct": round(range_60_pct, 3),
            "distance_to_high_30": round(distance_to_high_30, 3),
            "distance_to_low_30": round(distance_to_low_30, 3),
            "distance_to_high_60": round(distance_to_high_60, 3),
            "distance_to_low_60": round(distance_to_low_60, 3),
            "predicted_up_pct": round(predicted_up_pct, 3),
            "predicted_down_pct": round(predicted_down_pct, 3),
            "long_score": int(long_score),
            "short_score": int(short_score),
            "long_rr": round(long_rr, 2),
            "short_rr": round(short_rr, 2),
            "long_edge": round(long_edge, 2),
            "short_edge": round(short_edge, 2),
            "ai_signal": ai_signal,
            "ai_score": ai_score,
        }

        min_action_score = 50
        min_predicted_pct = DecisionEngine.COST_PCT * 0.95
        min_rr = 0.80

        allow_buy = (
            long_score >= min_action_score
            and predicted_up_pct >= min_predicted_pct
            and long_rr >= min_rr
            and long_edge >= short_edge - 1
        )

        allow_sell = (
            short_score >= min_action_score
            and predicted_down_pct >= min_predicted_pct
            and short_rr >= min_rr
            and short_edge >= long_edge - 1
        )

        if allow_buy and (long_edge >= short_edge):
            final_score = int(DecisionEngine._clamp(long_score, 50, 100))
            stop_loss = price * (1 - long_risk_pct / 100)
            take_profit = price * (1 + predicted_up_pct / 100)
            risk_reward = (take_profit - price) / max(price - stop_loss, 0.01)

            return {
                "action": "BUY",
                "score": final_score,
                "title": "預測上漲波段",
                "reason": "預估上漲空間大於下跌優勢，允許做多。",
                "reasons": long_reasons[:8],
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round(risk_reward, 2),
                "rebound": ai.get("rebound_prob", 55),
                "multi_period_status": "BULL_STRONG",
                "multi_period": {},
                "swing_state": "預測多方波段",
                "swing_prediction": swing_prediction,
                "predicted_up_pct": round(predicted_up_pct, 3),
                "predicted_down_pct": round(predicted_down_pct, 3),
                "long_rr": round(long_rr, 2),
                "short_rr": round(short_rr, 2),
            }

        if allow_sell and (short_edge > long_edge):
            final_score = int(DecisionEngine._clamp(short_score, 50, 100))
            stop_loss = price * (1 + short_risk_pct / 100)
            take_profit = price * (1 - predicted_down_pct / 100)
            risk_reward = (price - take_profit) / max(stop_loss - price, 0.01)

            return {
                "action": "SELL",
                "score": final_score,
                "title": "預測下跌波段",
                "reason": "預估下跌空間大於上漲優勢，允許做空。",
                "reasons": short_reasons[:8],
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round(risk_reward, 2),
                "rebound": ai.get("rebound_prob", 45),
                "multi_period_status": "BEAR_STRONG",
                "multi_period": {},
                "swing_state": "預測空方波段",
                "swing_prediction": swing_prediction,
                "predicted_up_pct": round(predicted_up_pct, 3),
                "predicted_down_pct": round(predicted_down_pct, 3),
                "long_rr": round(long_rr, 2),
                "short_rr": round(short_rr, 2),
            }

        wait_reasons = [
            f"多方分數 {long_score}",
            f"空方分數 {short_score}",
            f"預估上漲 {round(predicted_up_pct, 2)}%",
            f"預估下跌 {round(predicted_down_pct, 2)}%",
            f"多方風報 {round(long_rr, 2)}",
            f"空方風報 {round(short_rr, 2)}",
        ]

        return DecisionEngine._base_wait(
            price=price,
            score=max(long_score, short_score),
            title="等待更明確波段",
            reason="目前漲跌幅預測優勢不夠明顯。",
            extra={
                "reasons": wait_reasons,
                "swing_prediction": swing_prediction,
                "predicted_up_pct": round(predicted_up_pct, 3),
                "predicted_down_pct": round(predicted_down_pct, 3),
                "long_rr": round(long_rr, 2),
                "short_rr": round(short_rr, 2),
            },
        )
