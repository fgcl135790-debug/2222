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
    def _avg(values, n=20):
        if not values:
            return 0.0

        data = [
            DecisionEngine._safe_float(v)
            for v in values[-n:]
        ]

        if not data:
            return 0.0

        return sum(data) / len(data)

    @staticmethod
    def _recent_high(values, n=20):
        if not values:
            return 0.0

        data = [
            DecisionEngine._safe_float(v)
            for v in values[-n:]
        ]

        return max(data) if data else 0.0

    @staticmethod
    def _recent_low(values, n=20):
        if not values:
            return 0.0

        data = [
            DecisionEngine._safe_float(v)
            for v in values[-n:]
        ]

        return min(data) if data else 0.0

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
            "multi_period_status": "尚未套用多週期",
            "multi_period": {},
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

        ema5_v = DecisionEngine._last(ema5, price)
        ema20_v = DecisionEngine._last(ema20, price)
        ema60_v = DecisionEngine._last(ema60, price)

        rsi_v = DecisionEngine._last(rsi, 50)
        macd_v = DecisionEngine._last(macd, 0)
        macd_signal_v = DecisionEngine._last(macd_signal, 0)

        bid_ratio = DecisionEngine._safe_float(bid_ratio, 1.0)

        ai = ai or {}
        ai_signal = ai.get("signal", "WAIT")
        ai_score = int(DecisionEngine._safe_float(ai.get("score", 0), 0))

        avg_volume = DecisionEngine._avg(volumes, 20)
        now_volume = DecisionEngine._last(volumes, 0)
        volume_ratio = now_volume / max(avg_volume, 1)

        recent_high = DecisionEngine._recent_high(prices, 20)
        recent_low = DecisionEngine._recent_low(prices, 20)

        distance_to_high = 0.0
        distance_to_low = 0.0

        if price > 0:
            distance_to_high = (recent_high - price) / price * 100
            distance_to_low = (price - recent_low) / price * 100

        if price <= 0 or len(prices) < 35:
            return DecisionEngine._base_decision(
                action="WAIT",
                score=35,
                title="等待資料",
                reason="資料不足，暫不判斷",
                price=price,
            )

        # =========================
        # 盤整區直接 WAIT
        # =========================

        vwap_gap = 0.0
        if vwap > 0:
            vwap_gap = abs(price - vwap) / vwap * 100

        ema_gap = 0.0
        if ema20_v > 0:
            ema_gap = abs(ema5_v - ema20_v) / ema20_v * 100

        if vwap_gap < 0.08 and ema_gap < 0.05:
            return DecisionEngine._base_decision(
                action="WAIT",
                score=min(ai_score, 55),
                title="盤整不出手",
                reason="價格貼近 VWAP 且 EMA 差距過小，容易假突破",
                price=price,
            )

        # =========================
        # 做多嚴格條件
        # =========================

        long_pass = (
            ai_signal == "BUY"
            and ai_score >= 70
            and price > vwap
            and ema5_v > ema20_v
            and ema20_v >= ema60_v
            and macd_v >= macd_signal_v
            and 45 <= rsi_v <= 72
            and bid_ratio >= 1.0
            and volume_ratio >= 0.75
        )

        # 避免追高
        if distance_to_high < 0.12 and rsi_v > 68:
            long_pass = False

        # =========================
        # 做空嚴格條件
        # =========================

        short_pass = (
            ai_signal == "SELL"
            and ai_score >= 70
            and price < vwap
            and ema5_v < ema20_v
            and ema20_v <= ema60_v
            and macd_v <= macd_signal_v
            and 28 <= rsi_v <= 58
            and bid_ratio <= 1.05
            and volume_ratio >= 0.75
        )

        # 避免追空
        if distance_to_low < 0.12 and rsi_v < 32:
            short_pass = False

        # =========================
        # 產生決策
        # =========================

        if long_pass:
            stop_loss = price * 0.992
            take_profit = price * 1.017

            decision = {
                "action": "BUY",
                "score": min(100, ai_score),
                "title": "可當沖做多",
                "reason": "多方條件通過，等待進場確認",
                "reasons": ai.get("reasons", []),
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round((take_profit - price) / max(price - stop_loss, 0.01), 2),
                "rebound": ai.get("rebound_prob", 55),
                "multi_period_status": "多方等待共振",
                "multi_period": {},
            }

            return decision

        if short_pass:
            stop_loss = price * 1.008
            take_profit = price * 0.983

            decision = {
                "action": "SELL",
                "score": min(100, ai_score),
                "title": "可當沖做空",
                "reason": "空方條件通過，等待進場確認",
                "reasons": ai.get("reasons", []),
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round((price - take_profit) / max(stop_loss - price, 0.01), 2),
                "rebound": ai.get("rebound_prob", 45),
                "multi_period_status": "空方等待共振",
                "multi_period": {},
            }

            return decision

        return {
            "action": "WAIT",
            "score": min(ai_score, 65),
            "title": "等待確認",
            "reason": "AI 有訊號但未通過嚴格過濾，避免低勝率進場",
            "reasons": [
                f"AI 訊號：{ai_signal}",
                f"AI 分數：{ai_score}",
                "VWAP / EMA / MACD / RSI / 量能條件尚未完全通過",
            ],
            "entry_price": price,
            "stop_loss": 0,
            "take_profit": 0,
            "risk_reward": 0,
            "rebound": ai.get("rebound_prob", 50),
            "multi_period_status": "等待確認",
            "multi_period": {},
        }
