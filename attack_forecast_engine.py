import math


class AttackForecastEngine:
    """
    攻勢預判引擎。

    目的不是直接取代交易決策，而是在 BUY / SELL 真的成立前，先提示：
    - 多方是否正在蓄勢
    - 空方是否正在蓄勢
    - 是否仍只是雜訊 / 假攻擊

    只使用當下以前資料，不偷看未來。
    """

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            if isinstance(value, float) and math.isnan(value):
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _pct(now, prev):
        now = AttackForecastEngine._safe_float(now)
        prev = AttackForecastEngine._safe_float(prev)
        if prev <= 0:
            return 0.0
        return (now / prev - 1.0) * 100.0

    @staticmethod
    def _avg(values, default=0.0):
        vals = [AttackForecastEngine._safe_float(v) for v in values if v is not None]
        if not vals:
            return default
        return sum(vals) / len(vals)

    @staticmethod
    def _clamp(value, low=0, high=100):
        return max(low, min(high, value))

    @staticmethod
    def analyze(prices, volumes, vwap_values=None, bids=None, asks=None, decision=None):
        prices = [AttackForecastEngine._safe_float(x) for x in (prices or [])]
        volumes = [max(0.0, AttackForecastEngine._safe_float(x)) for x in (volumes or [])]
        vwap_values = [AttackForecastEngine._safe_float(x) for x in (vwap_values or [])]
        decision = decision or {}

        if len(prices) < 20:
            return {
                "direction": "WAIT",
                "title": "資料累積中",
                "score": 30,
                "urgency": "LOW",
                "message": "至少需要 20 筆盤中資料才判斷攻勢醞釀。",
                "reasons": ["資料不足，先避免提前預判。"],
                "features": {},
            }

        price = prices[-1]
        vwap = vwap_values[-1] if vwap_values and len(vwap_values) >= len(prices) else AttackForecastEngine._avg(prices[-20:], price)
        if vwap <= 0:
            vwap = price

        slope_1 = AttackForecastEngine._pct(prices[-1], prices[-2]) if len(prices) >= 2 else 0
        slope_3 = AttackForecastEngine._pct(prices[-1], prices[-4]) if len(prices) >= 4 else 0
        slope_5 = AttackForecastEngine._pct(prices[-1], prices[-6]) if len(prices) >= 6 else 0
        slope_10 = AttackForecastEngine._pct(prices[-1], prices[-11]) if len(prices) >= 11 else 0

        high_20 = max(prices[-20:])
        low_20 = min(prices[-20:])
        range_20_pct = (high_20 - low_20) / max(price, 0.000001) * 100
        near_high_pct = AttackForecastEngine._pct(price, high_20)
        near_low_pct = AttackForecastEngine._pct(low_20, price)
        vwap_gap = AttackForecastEngine._pct(price, vwap)

        vol_now = volumes[-1] if volumes else 0
        vol3 = AttackForecastEngine._avg(volumes[-3:], default=max(vol_now, 1))
        vol10_prev = AttackForecastEngine._avg(volumes[-13:-3], default=max(vol3, 1))
        vol20_prev = AttackForecastEngine._avg(volumes[-21:-1], default=max(vol_now, 1))
        vol_accel = vol3 / max(vol10_prev, 1)
        vol_ratio20 = vol_now / max(vol20_prev, 1)

        bid_total = sum(max(0.0, AttackForecastEngine._safe_float(x.get("size"))) for x in (bids or []) if isinstance(x, dict))
        ask_total = sum(max(0.0, AttackForecastEngine._safe_float(x.get("size"))) for x in (asks or []) if isinstance(x, dict))
        depth_total = max(bid_total + ask_total, 1.0)
        book_imbalance = (bid_total - ask_total) / depth_total

        already_trade = decision.get("action") in ["BUY", "SELL"] and AttackForecastEngine._safe_float(decision.get("score"), 0) >= 75

        long_score = 35
        short_score = 35
        long_reasons = []
        short_reasons = []
        penalties = []

        # 量先行：攻勢前通常先看到量能加速，但價格尚未完全突破。
        if vol_accel >= 1.4:
            long_score += 12
            short_score += 12
            long_reasons.append("近 3 筆量能已明顯高於前段，可能有攻擊前熱身。")
            short_reasons.append("近 3 筆量能已明顯高於前段，可能有殺盤前熱身。")
        elif vol_accel >= 1.15:
            long_score += 6
            short_score += 6
            long_reasons.append("量能開始放大，但還未到爆發。")
            short_reasons.append("量能開始放大，但還未到爆發。")

        if vol_ratio20 >= 1.6:
            long_score += 7
            short_score += 7
        elif vol_ratio20 < 0.55:
            long_score -= 8
            short_score -= 8
            penalties.append("目前量能偏乾，攻勢容易失敗。")

        # 委託簿：買盤/賣盤堆積。
        if book_imbalance > 0.20:
            long_score += 16
            short_score -= 8
            long_reasons.append("五檔委買明顯大於委賣，攻擊買盤可能提前卡位。")
        elif book_imbalance < -0.20:
            short_score += 16
            long_score -= 8
            short_reasons.append("五檔委賣明顯大於委買，空方賣壓可能提前集結。")
        elif abs(book_imbalance) < 0.08:
            penalties.append("五檔買賣力道接近平衡，提前訊號可信度普通。")

        # 價格位置：還沒真正突破但已貼近壓力/支撐，才叫提前預判；突破後就是交易決策。
        if slope_3 > 0.03 and slope_5 > 0.04:
            long_score += 10
            long_reasons.append("短線價格斜率轉強，接近向上攻擊。")
        if slope_3 < -0.03 and slope_5 < -0.04:
            short_score += 10
            short_reasons.append("短線價格斜率轉弱，接近向下攻擊。")

        if -0.12 <= near_high_pct <= 0.02 and slope_3 >= 0:
            long_score += 10
            long_reasons.append("價格貼近近 20 筆高點但尚未完全拉開，屬於攻擊前位置。")
        if -0.02 <= near_low_pct <= 0.12 and slope_3 <= 0:
            short_score += 10
            short_reasons.append("價格貼近近 20 筆低點但尚未完全灌破，屬於殺盤前位置。")

        if 0.05 <= vwap_gap <= 0.65:
            long_score += 7
            long_reasons.append("價格站在 VWAP 上方但未過度乖離，多方仍有推進空間。")
        elif vwap_gap > 1.0:
            long_score -= 13
            penalties.append("價格離 VWAP 太遠，提前追多容易變誘多。")
        elif vwap_gap < -0.8:
            long_score -= 16
            penalties.append("價格明顯在 VWAP 下方，多方預警降權，避免把護盤買牆誤判成上攻。")

        if -0.65 <= vwap_gap <= -0.05:
            short_score += 7
            short_reasons.append("價格壓在 VWAP 下方但未過度乖離，空方仍有推進空間。")
        elif vwap_gap < -1.0:
            short_score -= 13
            penalties.append("價格離 VWAP 太遠，提前追空容易被反彈洗掉。")
        elif vwap_gap > 0.8:
            short_score -= 16
            penalties.append("價格明顯在 VWAP 上方，空方預警降權，避免把賣牆誤判成下殺。")

        if range_20_pct < 0.22 and vol_accel >= 1.15:
            long_score += 5
            short_score += 5
            long_reasons.append("短區間壓縮後放量，容易出現方向攻擊。")
            short_reasons.append("短區間壓縮後放量，容易出現方向攻擊。")

        # 已經進入正式交易訊號時，降低「預判」語氣，避免與交易決策重複。
        if already_trade:
            long_score -= 8
            short_score -= 8
            penalties.append("交易決策已成立，攻勢預判降權，改以進出場規則為主。")

        long_score = AttackForecastEngine._clamp(long_score)
        short_score = AttackForecastEngine._clamp(short_score)

        if long_score >= short_score + 5 and long_score >= 62:
            direction = "LONG"
            score = int(long_score)
            title = "多方攻勢醞釀"
            message = "可能在正式 BUY 前先出現上攻準備。"
            reasons = long_reasons[:5]
        elif short_score >= long_score + 5 and short_score >= 62:
            direction = "SHORT"
            score = int(short_score)
            title = "空方攻勢醞釀"
            message = "可能在正式 SELL 前先出現下殺準備。"
            reasons = short_reasons[:5]
        else:
            direction = "WAIT"
            score = int(max(long_score, short_score))
            title = "尚未形成攻勢"
            message = "多空蓄勢分數接近，等待量價或五檔出現明確傾斜。"
            reasons = [
                f"多方蓄勢 {int(long_score)}｜空方蓄勢 {int(short_score)}",
                *(penalties[:3]),
            ]

        if not reasons:
            reasons = ["目前尚未出現可提前預判的量價組合。"]

        if score >= 78:
            urgency = "HIGH"
        elif score >= 65:
            urgency = "MEDIUM"
        else:
            urgency = "LOW"

        return {
            "direction": direction,
            "title": title,
            "score": score,
            "urgency": urgency,
            "message": message,
            "reasons": reasons + penalties[:2],
            "features": {
                "price": round(price, 2),
                "vwap_gap": round(vwap_gap, 3),
                "volume_acceleration": round(vol_accel, 2),
                "volume_ratio20": round(vol_ratio20, 2),
                "book_imbalance": round(book_imbalance, 3),
                "slope_3": round(slope_3, 3),
                "slope_5": round(slope_5, 3),
                "range_20_pct": round(range_20_pct, 3),
                "long_score": int(long_score),
                "short_score": int(short_score),
            },
        }
