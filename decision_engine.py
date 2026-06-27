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
    def _slope(values, n=8):
        if not values or len(values) < n + 1:
            return 0.0

        start = DecisionEngine._safe_float(values[-n])
        end = DecisionEngine._safe_float(values[-1])

        if start <= 0:
            return 0.0

        return (end - start) / start * 100

    @staticmethod
    def _recent_high(values, n=30):
        if not values:
            return 0.0

        data = [
            DecisionEngine._safe_float(v)
            for v in values[-n:]
        ]

        return max(data) if data else 0.0

    @staticmethod
    def _recent_low(values, n=30):
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
            "multi_period_status": "防守等待",
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

        if price <= 0 or len(prices) < 45:
            return DecisionEngine._base_decision(
                action="WAIT",
                score=35,
                title="等待資料",
                reason="資料不足，至少等待 45 筆資料",
                price=price,
            )

        avg_volume = DecisionEngine._avg(volumes, 20)
        now_volume = DecisionEngine._last(volumes, 0)
        volume_ratio = now_volume / max(avg_volume, 1)

        price_slope = DecisionEngine._slope(prices, 10)
        ema20_slope = DecisionEngine._slope(ema20 if isinstance(ema20, list) else [], 10)

        recent_high = DecisionEngine._recent_high(prices, 30)
        recent_low = DecisionEngine._recent_low(prices, 30)

        distance_to_high = 0.0
        distance_to_low = 0.0

        if price > 0:
            distance_to_high = (recent_high - price) / price * 100
            distance_to_low = (price - recent_low) / price * 100

        vwap_gap = 0.0

        if vwap > 0:
            vwap_gap = (price - vwap) / vwap * 100

        ema_gap = 0.0

        if ema20_v > 0:
            ema_gap = (ema5_v - ema20_v) / ema20_v * 100

        macd_gap = macd_v - macd_signal_v

        # =========================
        # 盤整區不做
        # =========================

        flat_market = (
            abs(vwap_gap) < 0.10
            and abs(ema_gap) < 0.06
            and abs(price_slope) < 0.10
        )

        if flat_market:
            return DecisionEngine._base_decision(
                action="WAIT",
                score=min(ai_score, 55),
                title="盤整不出手",
                reason="價格貼近 VWAP、EMA 差距小，容易被洗掉",
                price=price,
            )

        # =========================
        # 不追價過濾
        # =========================

        chase_long = (
            distance_to_high < 0.18
            and rsi_v >= 63
        )

        chase_short = (
            distance_to_low < 0.18
            and rsi_v <= 38
        )

        vwap_too_far_long = vwap_gap > 0.85
        vwap_too_far_short = vwap_gap < -0.85

        weak_volume = volume_ratio < 0.85

        # =========================
        # BUY 條件：只做「強勢回踩後再上」
        # =========================

        long_pass = (
            ai_signal == "BUY"
            and ai_score >= 78
            and price > vwap
            and ema5_v > ema20_v
            and ema20_v > ema60_v
            and macd_v > macd_signal_v
            and macd_gap > 0
            and 48 <= rsi_v <= 65
            and price_slope > 0
            and ema20_slope >= 0
            and volume_ratio >= 0.85
            and bid_ratio >= 1.03
            and not chase_long
            and not vwap_too_far_long
        )

        # =========================
        # SELL 條件：只做「弱勢反彈失敗」
        # =========================

        short_pass = (
            ai_signal == "SELL"
            and ai_score >= 78
            and price < vwap
            and ema5_v < ema20_v
            and ema20_v < ema60_v
            and macd_v < macd_signal_v
            and macd_gap < 0
            and 35 <= rsi_v <= 55
            and price_slope < 0
            and ema20_slope <= 0
            and volume_ratio >= 0.85
            and bid_ratio <= 0.98
            and not chase_short
            and not vwap_too_far_short
        )

        # =========================
        # 額外防守：量能不足直接不做
        # =========================

        if weak_volume:
            return DecisionEngine._base_decision(
                action="WAIT",
                score=min(ai_score, 60),
                title="量能不足",
                reason="成交量低於均量，訊號容易失真",
                price=price,
            )

        # =========================
        # 輸出決策
        # =========================

        if long_pass:
            stop_loss = price * 0.993
            take_profit = price * 1.015

            return {
                "action": "BUY",
                "score": min(100, ai_score),
                "title": "防守型做多",
                "reason": "多方趨勢成立，且未明顯追高",
                "reasons": [
                    "價格站上 VWAP",
                    "EMA 多頭排列",
                    "MACD 多方",
                    "RSI 未過熱",
                    "非追高區",
                    "量能通過",
                ],
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round((take_profit - price) / max(price - stop_loss, 0.01), 2),
                "rebound": ai.get("rebound_prob", 55),
                "multi_period_status": "防守多方",
                "multi_period": {},
            }

        if short_pass:
            stop_loss = price * 1.007
            take_profit = price * 0.985

            return {
                "action": "SELL",
                "score": min(100, ai_score),
                "title": "防守型做空",
                "reason": "空方趨勢成立，且未明顯追空",
                "reasons": [
                    "價格跌破 VWAP",
                    "EMA 空頭排列",
                    "MACD 空方",
                    "RSI 未過低",
                    "非追空區",
                    "量能通過",
                ],
                "entry_price": price,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "risk_reward": round((price - take_profit) / max(stop_loss - price, 0.01), 2),
                "rebound": ai.get("rebound_prob", 45),
                "multi_period_status": "防守空方",
                "multi_period": {},
            }

        block_reasons = [
            f"AI 訊號：{ai_signal}",
            f"AI 分數：{ai_score}",
            f"VWAP 距離：{round(vwap_gap, 2)}%",
            f"量能倍率：{round(volume_ratio, 2)}",
            f"RSI：{round(rsi_v, 1)}",
            "未通過防守型進場條件",
        ]

        if chase_long:
            block_reasons.append("接近短線高點，不追多")

        if chase_short:
            block_reasons.append("接近短線低點，不追空")

        if vwap_too_far_long:
            block_reasons.append("價格離 VWAP 過遠，不追多")

        if vwap_too_far_short:
            block_reasons.append("價格離 VWAP 過遠，不追空")

        return {
            "action": "WAIT",
            "score": min(ai_score, 70),
            "title": "防守等待",
            "reason": "AI 有訊號但未通過防守型濾網",
            "reasons": block_reasons,
            "entry_price": price,
            "stop_loss": 0,
            "take_profit": 0,
            "risk_reward": 0,
            "rebound": ai.get("rebound_prob", 50),
            "multi_period_status": "防守等待",
            "multi_period": {},
        }
