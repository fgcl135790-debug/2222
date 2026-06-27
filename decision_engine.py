class DecisionEngine:

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _clamp(value, low=0, high=100):
        return max(low, min(high, value))

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
    ):

        price = DecisionEngine._safe_float(price)
        vwap = DecisionEngine._safe_float(vwap)
        ema5 = DecisionEngine._safe_float(ema5)
        ema20 = DecisionEngine._safe_float(ema20)
        ema60 = DecisionEngine._safe_float(ema60)
        rsi = DecisionEngine._safe_float(rsi)
        macd = DecisionEngine._safe_float(macd)
        macd_signal = DecisionEngine._safe_float(macd_signal)
        bid_ratio = DecisionEngine._safe_float(bid_ratio, 1.0)

        signal = ai.get("signal", "HOLD")
        ai_score = int(ai.get("score", 50))
        rebound = int(ai.get("rebound_prob", 50))
        market_state = ai.get("market_state", "未知狀態")

        long_score = 0
        short_score = 0
        reasons = []

        # =========================
        # AI 原始方向
        # =========================
        if signal == "BUY":
            long_score += 2
            reasons.append("AI 原始訊號偏多")

        elif signal == "SELL":
            short_score += 2
            reasons.append("AI 原始訊號偏空")

        else:
            reasons.append("AI 原始訊號觀望")

        # =========================
        # 均線結構
        # =========================
        if ema5 > ema20 > ema60:
            long_score += 3
            reasons.append("EMA5 > EMA20 > EMA60，多頭排列")

        elif ema5 < ema20 < ema60:
            short_score += 3
            reasons.append("EMA5 < EMA20 < EMA60，空頭排列")

        elif ema5 > ema20:
            long_score += 1
            reasons.append("EMA5 站上 EMA20，短線偏多")

        elif ema5 < ema20:
            short_score += 1
            reasons.append("EMA5 跌破 EMA20，短線偏空")

        # =========================
        # VWAP
        # =========================
        if vwap > 0:

            if price > vwap:
                long_score += 2
                reasons.append("價格站上 VWAP，多方有支撐")

            elif price < vwap:
                short_score += 2
                reasons.append("價格跌破 VWAP，空方壓力較大")

        # =========================
        # MACD
        # =========================
        if macd > macd_signal:
            long_score += 1
            reasons.append("MACD 位於多方")

        elif macd < macd_signal:
            short_score += 1
            reasons.append("MACD 位於空方")

        # =========================
        # RSI
        # =========================
        if 40 <= rsi <= 65:
            long_score += 1
            reasons.append("RSI 位於健康區間")

        elif rsi > 75:
            short_score += 1
            reasons.append("RSI 過熱，追多風險提高")

        elif rsi < 30:
            long_score += 1
            reasons.append("RSI 超賣，可能有反彈機會")

        # =========================
        # 五檔主力
        # =========================
        if bid_ratio >= 1.5:
            long_score += 3
            reasons.append("五檔買盤明顯大於賣盤，主力偏多")

        elif bid_ratio >= 1.2:
            long_score += 1
            reasons.append("五檔買盤略強")

        elif bid_ratio <= 0.6:
            short_score += 3
            reasons.append("五檔賣壓明顯大於買盤，主力偏空")

        elif bid_ratio <= 0.8:
            short_score += 1
            reasons.append("五檔賣壓略強")

        # =========================
        # 反彈率
        # =========================
        if rebound >= 65:
            long_score += 2
            reasons.append(f"反彈率 {rebound}%，反彈條件偏強")

        elif rebound <= 35:
            short_score += 2
            reasons.append(f"反彈率 {rebound}%，反彈條件偏弱")

        else:
            reasons.append(f"反彈率 {rebound}%，多空仍在拉鋸")

        # =========================
        # 決策分數
        # =========================
        bias = long_score - short_score

        confidence = 50 + abs(bias) * 6

        if ai_score >= 70:
            confidence += 8
        elif ai_score <= 40:
            confidence -= 8

        confidence = int(
            DecisionEngine._clamp(confidence)
        )

        # =========================
        # 決策
        # 台股：BUY = 做多 = 紅
        # 台股：SELL = 做空 = 綠
        # =========================
        if bias >= 4 and confidence >= 60:

            action = "BUY"

            entry_low = round(price * 0.998, 2)
            entry_high = round(price * 1.002, 2)

            stop_loss = round(price * 0.994, 2)
            take_profit = round(price * 1.012, 2)

            risk_value = price - stop_loss
            reward_value = take_profit - price

            rr = round(
                reward_value / risk_value,
                2
            ) if risk_value > 0 else "-"

            entry = f"{entry_low} ~ {entry_high}"

            reasons.append("V7.5 決策：多方條件成立")
            reasons.append("策略：回測進場區再考慮做多，避免追高")

        elif bias <= -4 and confidence >= 60:

            action = "SELL"

            entry_low = round(price * 0.998, 2)
            entry_high = round(price * 1.002, 2)

            stop_loss = round(price * 1.006, 2)
            take_profit = round(price * 0.988, 2)

            risk_value = stop_loss - price
            reward_value = price - take_profit

            rr = round(
                reward_value / risk_value,
                2
            ) if risk_value > 0 else "-"

            entry = f"{entry_low} ~ {entry_high}"

            reasons.append("V7.5 決策：空方條件成立")
            reasons.append("策略：反彈不過壓力區可偏空，不追空")

        else:

            action = "WAIT"

            entry = "-"
            stop_loss = "-"
            take_profit = "-"
            rr = "-"

            reasons.append("V7.5 決策：多空條件不足")
            reasons.append("策略：等待方向確認，不建議進場")

        return {

            "action": action,

            "score": confidence,

            "entry": entry,

            "stop_loss": stop_loss,

            "take_profit": take_profit,

            "rr": rr,

            "rebound": rebound,

            "long_score": long_score,

            "short_score": short_score,

            "bias": bias,

            "reasons": reasons,

        }
