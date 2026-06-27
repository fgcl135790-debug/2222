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
    def generate(ai, price):

        price = DecisionEngine._safe_float(price)

        signal = ai.get("signal", "HOLD")
        ai_score = int(ai.get("score", 50))
        rebound = int(ai.get("rebound_prob", 50))
        market_state = ai.get("market_state", "未知狀態")

        # =========================
        # V7.5 決策分數
        # =========================

        decision_score = ai_score

        if rebound >= 65:
            decision_score += 8
        elif rebound <= 35:
            decision_score -= 8

        if signal == "BUY":
            decision_score += 8
        elif signal == "SELL":
            decision_score += 8
        else:
            decision_score -= 10

        decision_score = int(
            DecisionEngine._clamp(decision_score)
        )

        # =========================
        # 交易門檻
        # =========================

        reasons = []

        reasons.append(f"AI信心 {ai_score}%")
        reasons.append(f"反彈率 {rebound}%")
        reasons.append(market_state)

        # =========================
        # BUY：台股做多
        # =========================

        if signal == "BUY" and decision_score >= 60:

            action = "BUY"

            entry_low = round(price * 0.998, 2)
            entry_high = round(price * 1.002, 2)

            stop_loss = round(price * 0.994, 2)
            take_profit = round(price * 1.012, 2)

            risk = price - stop_loss
            reward = take_profit - price

            rr = round(
                reward / risk,
                2
            ) if risk > 0 else 0

            entry = f"{entry_low} ~ {entry_high}"

            reasons.append("V7.5 判定：多方條件成立")
            reasons.append("策略：等待回測進場區，不追價")

        # =========================
        # SELL：台股做空
        # =========================

        elif signal == "SELL" and decision_score >= 60:

            action = "SELL"

            entry_low = round(price * 0.998, 2)
            entry_high = round(price * 1.002, 2)

            stop_loss = round(price * 1.006, 2)
            take_profit = round(price * 0.988, 2)

            risk = stop_loss - price
            reward = price - take_profit

            rr = round(
                reward / risk,
                2
            ) if risk > 0 else 0

            entry = f"{entry_low} ~ {entry_high}"

            reasons.append("V7.5 判定：空方條件成立")
            reasons.append("策略：反彈不過壓力區可偏空")

        # =========================
        # WAIT：不交易
        # =========================

        else:

            action = "WAIT"

            entry = "-"
            stop_loss = "-"
            take_profit = "-"
            rr = "-"

            reasons.append("V7.5 判定：條件不足，不建議進場")
            reasons.append("策略：等待 AI 信心與方向同步")

        # =========================
        # 回傳給 Decision Card
        # =========================

        return {

            "action": action,

            "score": decision_score,

            "entry": entry,

            "stop_loss": stop_loss,

            "take_profit": take_profit,

            "rr": rr,

            "rebound": rebound,

            "reasons": reasons,

        }
