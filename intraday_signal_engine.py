import math

from tape_flow_engine import TapeFlowEngine
from orderbook_flow_engine import OrderBookFlowEngine
from market_context_engine import MarketContextEngine
from adaptive_risk_engine import AdaptiveRiskEngine


class IntradaySignalEngine:
    """
    專業即時結構 AI v2。

    不訓練、不偷看未來、不用每日候選。
    每一根 K 只使用當下以前資料，並把專業當沖會看的資料分層：
    - ORB / VWAP / 動能斜率
    - Tape Flow 主動買賣量 proxy
    - 五檔委託簿壓力（真實盤有五檔；歷史回測用中性）
    - 盤勢分類：趨勢盤 / VWAP 震盪 / 低波動盤
    - 動態停損停利：依 ATR / ORB / 當日波動調整

    這版的目的不是硬湊每天交易，而是讓 AI 判斷更多「當下已知的盤中結構」，
    避免只靠 1 分 K 技術指標慢半拍。
    """

    DEFAULT_STOP_PCT = 0.7
    DEFAULT_TAKE_PCT = 1.8
    DEFAULT_COST_PCT = 0.435

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
        now = IntradaySignalEngine._safe_float(now)
        prev = IntradaySignalEngine._safe_float(prev)
        if prev <= 0:
            return 0.0
        return (now / prev - 1.0) * 100.0

    @staticmethod
    def _avg(values, default=0.0):
        vals = [IntradaySignalEngine._safe_float(v) for v in values if v is not None]
        if not vals:
            return default
        return sum(vals) / len(vals)

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def required_win_rate_pct(stop_pct=0.7, take_pct=1.8, cost_pct=0.435, safety_margin=0.0):
        stop_pct = IntradaySignalEngine._safe_float(stop_pct, 0.7)
        take_pct = IntradaySignalEngine._safe_float(take_pct, 1.8)
        cost_pct = IntradaySignalEngine._safe_float(cost_pct, 0.435)
        win_net = max(take_pct - cost_pct, 0.000001)
        loss_net = stop_pct + cost_pct
        return round((loss_net / max(win_net + loss_net, 0.000001)) * 100 + safety_margin, 2)

    @staticmethod
    def estimate_ev(win_rate_pct, stop_pct=0.7, take_pct=1.8, cost_pct=0.435):
        p = IntradaySignalEngine._clamp(win_rate_pct, 0, 100) / 100.0
        win_net = take_pct - cost_pct
        loss_net = stop_pct + cost_pct
        return p * win_net - (1 - p) * loss_net

    @staticmethod
    def _score_to_win_rate(score, required_win_rate, context_quality=50.0):
        """
        把結構分數轉成保守勝率估計。
        - 55 分附近接近損益兩平以下
        - 70 分才略高於損益兩平
        - 80+ 才視為品質較好
        context_quality 用來反映當日盤勢是否適合交易。
        """
        score = IntradaySignalEngine._safe_float(score)
        context_adj = (IntradaySignalEngine._safe_float(context_quality, 50) - 50.0) * 0.12
        wr = required_win_rate - 4.0 + (score - 55.0) * 0.72 + context_adj
        return IntradaySignalEngine._clamp(wr, 22.0, 84.0)

    @staticmethod
    def _build_features(
        prices,
        volumes,
        opens=None,
        highs=None,
        lows=None,
        vwap_values=None,
        time_values=None,
    ):
        prices = [IntradaySignalEngine._safe_float(x) for x in (prices or [])]
        volumes = [IntradaySignalEngine._safe_float(x) for x in (volumes or [])]
        n = len(prices)
        if n < 16:
            return None

        opens = [IntradaySignalEngine._safe_float(x) for x in (opens or prices)]
        highs = [IntradaySignalEngine._safe_float(x) for x in (highs or prices)]
        lows = [IntradaySignalEngine._safe_float(x) for x in (lows or prices)]
        if len(opens) < n:
            opens = (opens + prices[len(opens):])[:n]
        if len(highs) < n:
            highs = (highs + prices[len(highs):])[:n]
        if len(lows) < n:
            lows = (lows + prices[len(lows):])[:n]

        price = prices[-1]
        minute_index = n - 1

        if vwap_values and len(vwap_values) >= n:
            vwap = IntradaySignalEngine._safe_float(vwap_values[-1], price)
        else:
            amount = 0.0
            vol_sum = 0.0
            for p, v in zip(prices, volumes):
                amount += p * max(v, 0)
                vol_sum += max(v, 0)
            vwap = amount / vol_sum if vol_sum > 0 else price

        orb_len = min(15, n)
        orb_high = max(highs[:orb_len]) if highs[:orb_len] else price
        orb_low = min(lows[:orb_len]) if lows[:orb_len] else price
        day_high = max(highs)
        day_low = min(lows)
        day_range_pct = (day_high - day_low) / max(price, 0.000001) * 100

        slope_1 = IntradaySignalEngine._pct(price, prices[-2]) if n >= 2 else 0
        slope_3 = IntradaySignalEngine._pct(price, prices[-4]) if n >= 4 else 0
        slope_5 = IntradaySignalEngine._pct(price, prices[-6]) if n >= 6 else 0
        slope_10 = IntradaySignalEngine._pct(price, prices[-11]) if n >= 11 else 0
        slope_20 = IntradaySignalEngine._pct(price, prices[-21]) if n >= 21 else slope_10

        vol_now = volumes[-1] if volumes else 0.0
        vol5 = IntradaySignalEngine._avg(volumes[-6:-1], default=max(vol_now, 1.0))
        vol20 = IntradaySignalEngine._avg(volumes[-21:-1], default=max(vol_now, 1.0))
        recent3 = IntradaySignalEngine._avg(volumes[-3:], default=max(vol_now, 1.0))
        prev10 = IntradaySignalEngine._avg(volumes[-13:-3], default=max(recent3, 1.0))
        volume_ratio_5 = vol_now / max(vol5, 1.0)
        volume_ratio_20 = vol_now / max(vol20, 1.0)
        volume_acceleration = recent3 / max(prev10, 1.0)

        high_now = highs[-1]
        low_now = lows[-1]
        open_now = opens[-1]
        candle_range = max(high_now - low_now, 0.000001)
        close_location = (price - low_now) / candle_range
        upper_wick_pct = (high_now - max(open_now, price)) / max(price, 0.000001) * 100
        lower_wick_pct = (min(open_now, price) - low_now) / max(price, 0.000001) * 100

        pullback_from_high = (day_high - price) / max(price, 0.000001) * 100
        rebound_from_low = (price - day_low) / max(price, 0.000001) * 100

        return {
            "price": price,
            "minute_index": minute_index,
            "vwap": vwap,
            "vwap_gap": IntradaySignalEngine._pct(price, vwap),
            "orb_high": orb_high,
            "orb_low": orb_low,
            "orb_high_gap": IntradaySignalEngine._pct(price, orb_high),
            "orb_low_gap": IntradaySignalEngine._pct(price, orb_low),
            "day_high": day_high,
            "day_low": day_low,
            "day_range_pct": day_range_pct,
            "distance_to_high": abs(IntradaySignalEngine._pct(day_high, price)),
            "distance_to_low": abs(IntradaySignalEngine._pct(price, day_low)),
            "pullback_from_high": pullback_from_high,
            "rebound_from_low": rebound_from_low,
            "slope_1": slope_1,
            "slope_3": slope_3,
            "slope_5": slope_5,
            "slope_10": slope_10,
            "slope_20": slope_20,
            "volume_ratio_5": volume_ratio_5,
            "volume_ratio_20": volume_ratio_20,
            "volume_acceleration": volume_acceleration,
            "close_location": close_location,
            "upper_wick_pct": upper_wick_pct,
            "lower_wick_pct": lower_wick_pct,
        }

    @staticmethod
    def _direction_score(feature, action, tape, orderbook, market_context):
        f = feature
        score = 42.0
        reasons = []
        penalties = []

        minute = int(f.get("minute_index", 0))
        vwap_gap = f.get("vwap_gap", 0.0)
        orb_high_gap = f.get("orb_high_gap", 0.0)
        orb_low_gap = f.get("orb_low_gap", 0.0)
        slope1 = f.get("slope_1", 0.0)
        slope3 = f.get("slope_3", 0.0)
        slope5 = f.get("slope_5", 0.0)
        slope10 = f.get("slope_10", 0.0)
        slope20 = f.get("slope_20", 0.0)
        vr5 = f.get("volume_ratio_5", 1.0)
        vr20 = f.get("volume_ratio_20", 1.0)
        vacc = f.get("volume_acceleration", 1.0)
        close_loc = f.get("close_location", 0.5)
        upper_wick = f.get("upper_wick_pct", 0.0)
        lower_wick = f.get("lower_wick_pct", 0.0)
        dist_high = f.get("distance_to_high", 0.0)
        dist_low = f.get("distance_to_low", 0.0)
        day_range = f.get("day_range_pct", 0.0)

        tape_buy = tape.get("buy_pressure", 50)
        tape_sell = tape.get("sell_pressure", 50)
        ob_buy = orderbook.get("buy_pressure", 50)
        ob_sell = orderbook.get("sell_pressure", 50)
        context_trend = market_context.get("trend", "WAIT")
        context_quality = market_context.get("quality", 50)
        regime = market_context.get("regime", "MIXED")

        # 盤勢品質先當底層濾網。
        score += (context_quality - 50) * 0.18
        if day_range < 0.9:
            score -= 7
            penalties.append("當日區間偏小，停利空間不足。")

        if action == "BUY":
            # 三種做多型態：突破、VWAP 拉回再攻、急跌後轉強反彈。
            breakout = orb_high_gap >= -0.03 and slope3 > 0.05
            vwap_reclaim = -0.25 <= vwap_gap <= 0.45 and slope3 > 0.06 and close_loc >= 0.55
            rebound = vwap_gap < -0.25 and slope1 > 0 and slope3 > 0.08 and close_loc >= 0.62 and tape_buy >= 55

            if breakout:
                score += 13
                reasons.append("做多型態：接近或突破 ORB High，短線開始轉強。")
            if orb_high_gap >= 0.05:
                score += 6
                reasons.append("價格已突破 ORB High。")
            if vwap_reclaim:
                score += 12
                reasons.append("做多型態：VWAP 附近拉回後重新轉強。")
            if rebound:
                score += 8
                reasons.append("做多型態：急跌後短線反彈且成交流改善。")
            if vwap_gap >= 0.03:
                score += 6
                reasons.append("價格站上 VWAP。")

            if slope3 > 0.10:
                score += 5
            if slope5 > 0.18:
                score += 5
            if slope10 > 0.30:
                score += 4
            if slope20 > 0.40:
                score += 3
            if close_loc >= 0.62:
                score += 4
            if vr5 >= 1.2 or vacc >= 1.12:
                score += 6
                reasons.append("量能脈衝放大。")
            if vr5 >= 1.7 or vr20 >= 1.5:
                score += 4

            # Tape / Orderbook：有方向就加，反向就扣。
            score += (tape_buy - 50) * 0.22
            score += (ob_buy - 50) * 0.10
            if tape_buy >= 60:
                reasons.append("成交流偏主動買。")
            if orderbook.get("available") and ob_buy >= 60:
                reasons.append("五檔承接偏強。")
            if context_trend == "BUY":
                score += 5
                reasons.append("盤勢分類偏多，順勢做多加分。")
            elif context_trend == "SELL":
                score -= 6
                penalties.append("盤勢分類偏空，逆勢做多需降分。")

            if vwap_gap < -0.65 and slope3 <= 0:
                score -= 15
                penalties.append("價格仍在 VWAP 下且未轉強，做多風險高。")
            if vwap_gap > 1.75 and dist_high <= 0.30:
                score -= 15
                penalties.append("離 VWAP 過遠且靠近日高，追高風險。")
            if upper_wick > lower_wick * 1.25 and close_loc < 0.50:
                score -= 7
                penalties.append("上影線壓力較大。")
            if tape.get("absorption_risk", 0) >= 12 and tape_buy > tape_sell:
                score -= 6
                penalties.append("放量但價格推不動，疑似上方吸收。")
            if vr5 < 0.5 and vacc < 0.75:
                score -= 7
                penalties.append("量能不足，做多延續性偏弱。")

        else:
            breakout = orb_low_gap <= 0.03 and slope3 < -0.05
            vwap_fail = -0.45 <= vwap_gap <= 0.25 and slope3 < -0.06 and close_loc <= 0.45
            flush = vwap_gap > 0.25 and slope1 < 0 and slope3 < -0.08 and close_loc <= 0.38 and tape_sell >= 55

            if breakout:
                score += 13
                reasons.append("做空型態：接近或跌破 ORB Low，短線開始轉弱。")
            if orb_low_gap <= -0.05:
                score += 6
                reasons.append("價格已跌破 ORB Low。")
            if vwap_fail:
                score += 12
                reasons.append("做空型態：VWAP 附近反彈失敗。")
            if flush:
                score += 8
                reasons.append("做空型態：急拉後轉弱且成交流轉賣。")
            if vwap_gap <= -0.03:
                score += 6
                reasons.append("價格跌破 VWAP。")

            if slope3 < -0.10:
                score += 5
            if slope5 < -0.18:
                score += 5
            if slope10 < -0.30:
                score += 4
            if slope20 < -0.40:
                score += 3
            if close_loc <= 0.38:
                score += 4
            if vr5 >= 1.2 or vacc >= 1.12:
                score += 6
                reasons.append("量能脈衝放大。")
            if vr5 >= 1.7 or vr20 >= 1.5:
                score += 4

            score += (tape_sell - 50) * 0.22
            score += (ob_sell - 50) * 0.10
            if tape_sell >= 60:
                reasons.append("成交流偏主動賣。")
            if orderbook.get("available") and ob_sell >= 60:
                reasons.append("五檔賣壓偏強。")
            if context_trend == "SELL":
                score += 5
                reasons.append("盤勢分類偏空，順勢做空加分。")
            elif context_trend == "BUY":
                score -= 6
                penalties.append("盤勢分類偏多，逆勢做空需降分。")

            if vwap_gap > 0.65 and slope3 >= 0:
                score -= 15
                penalties.append("價格仍在 VWAP 上且未轉弱，做空風險高。")
            if vwap_gap < -1.75 and dist_low <= 0.30:
                score -= 15
                penalties.append("低於 VWAP 過遠且靠近日低，追空風險。")
            if lower_wick > upper_wick * 1.25 and close_loc > 0.50:
                score -= 7
                penalties.append("下影線支撐較明顯。")
            if tape.get("absorption_risk", 0) >= 12 and tape_sell > tape_buy:
                score -= 6
                penalties.append("放量但價格跌不動，疑似下方吸收。")
            if vr5 < 0.5 and vacc < 0.75:
                score -= 7
                penalties.append("量能不足，做空延續性偏弱。")

        # 時段風險：專業當沖不是完全禁止午盤，但門檻要提高。
        if minute >= 230:
            score -= 9
            penalties.append("12:50 後新倉，停利空間與隔日風險較高。")
        elif minute >= 180:
            score -= 5
            penalties.append("12:00 後新倉，量縮與假突破風險提高。")
        elif minute >= 150:
            score -= 2
            penalties.append("11:30 後新倉，需確認量能延續。")

        score = IntradaySignalEngine._clamp(score, 0, 100)
        return score, reasons, penalties

    @staticmethod
    def analyze(
        prices,
        volumes,
        opens=None,
        highs=None,
        lows=None,
        vwap_values=None,
        time_values=None,
        bids=None,
        asks=None,
        stop_pct=0.7,
        take_pct=1.8,
        cost_pct=0.435,
        min_score=66,
        min_expected_value=0.02,
        use_adaptive_risk=True,
    ):
        feature = IntradaySignalEngine._build_features(
            prices=prices,
            volumes=volumes,
            opens=opens,
            highs=highs,
            lows=lows,
            vwap_values=vwap_values,
            time_values=time_values,
        )
        if feature is None:
            return IntradaySignalEngine._wait("盤中資料不足，至少需要 16 根 K。")

        tape = TapeFlowEngine.analyze(prices=prices, volumes=volumes)
        orderbook = OrderBookFlowEngine.analyze(bids=bids, asks=asks, price=feature.get("price"))
        market_context = MarketContextEngine.analyze(
            prices=prices,
            volumes=volumes,
            highs=highs,
            lows=lows,
            vwap_values=vwap_values,
        )
        risk_plan = AdaptiveRiskEngine.suggest(
            prices=prices,
            highs=highs,
            lows=lows,
            volumes=volumes,
            base_stop_pct=stop_pct,
            base_take_pct=take_pct,
            cost_pct=cost_pct,
        ) if use_adaptive_risk else {
            "stop_pct": stop_pct,
            "take_pct": take_pct,
            "risk_reward": round(take_pct / max(stop_pct, 0.01), 2),
            "mode": "base",
            "reasons": ["使用固定停損停利。"],
        }

        eff_stop = risk_plan.get("stop_pct", stop_pct)
        eff_take = risk_plan.get("take_pct", take_pct)
        required = IntradaySignalEngine.required_win_rate_pct(eff_stop, eff_take, cost_pct, safety_margin=0.0)

        buy_score, buy_reasons, buy_penalties = IntradaySignalEngine._direction_score(
            feature, "BUY", tape=tape, orderbook=orderbook, market_context=market_context
        )
        sell_score, sell_reasons, sell_penalties = IntradaySignalEngine._direction_score(
            feature, "SELL", tape=tape, orderbook=orderbook, market_context=market_context
        )

        context_quality = market_context.get("quality", 50)
        buy_wr = IntradaySignalEngine._score_to_win_rate(buy_score, required, context_quality=context_quality)
        sell_wr = IntradaySignalEngine._score_to_win_rate(sell_score, required, context_quality=context_quality)
        buy_ev = IntradaySignalEngine.estimate_ev(buy_wr, eff_stop, eff_take, cost_pct)
        sell_ev = IntradaySignalEngine.estimate_ev(sell_wr, eff_stop, eff_take, cost_pct)

        buy = {
            "action": "BUY",
            "score": round(buy_score, 2),
            "win_rate": round(buy_wr, 2),
            "expected_value": round(buy_ev, 3),
            "reasons": buy_reasons,
            "penalties": buy_penalties,
            "sample_count": 0,
            "profit_factor": 0,
            "setup_type": "即時結構做多",
        }
        sell = {
            "action": "SELL",
            "score": round(sell_score, 2),
            "win_rate": round(sell_wr, 2),
            "expected_value": round(sell_ev, 3),
            "reasons": sell_reasons,
            "penalties": sell_penalties,
            "sample_count": 0,
            "profit_factor": 0,
            "setup_type": "即時結構做空",
        }

        # 方向選擇：分數 + EV + 成交流方向，避免只靠分數。
        buy_edge = buy_score + buy_ev * 20 + (tape.get("buy_pressure", 50) - 50) * 0.10
        sell_edge = sell_score + sell_ev * 20 + (tape.get("sell_pressure", 50) - 50) * 0.10
        chosen = buy if buy_edge >= sell_edge else sell

        can_trade = (
            chosen["score"] >= min_score
            and chosen["expected_value"] >= min_expected_value
            and chosen["win_rate"] >= required
        )

        common_reasons = []
        common_reasons.extend(market_context.get("reasons", [])[:2])
        common_reasons.extend(tape.get("reasons", [])[:2])
        if orderbook.get("available"):
            common_reasons.extend(orderbook.get("reasons", [])[:2])
        common_reasons.extend(risk_plan.get("reasons", [])[:2])

        base_payload = {
            "buy": buy,
            "sell": sell,
            "chosen": chosen,
            "required_win_rate": required,
            "risk_plan": risk_plan,
            "tape_flow": tape,
            "orderbook_flow": orderbook,
            "market_context": market_context,
            "feature": feature,
            "adaptive_stop_pct": eff_stop,
            "adaptive_take_pct": eff_take,
        }

        if not can_trade:
            return {
                **base_payload,
                "decision": "WAIT",
                "action": "WAIT",
                "score": int(max(0, min(86, max(buy_score, sell_score)))),
                "title": "即時結構未達出手標準",
                "reason": "當下成交流、委託簿、盤勢與扣成本期望尚未同步。",
                "reasons": [
                    f"BUY 分數 {buy['score']}｜勝率估 {buy['win_rate']}%｜EV {buy['expected_value']}%",
                    f"SELL 分數 {sell['score']}｜勝率估 {sell['win_rate']}%｜EV {sell['expected_value']}%",
                    f"需求勝率 {required}%｜最低 EV {min_expected_value}%｜最低 Score {min_score}",
                    *(common_reasons[:5]),
                    *(chosen.get("penalties", [])[:3]),
                ],
                "risk_level": "HIGH",
                "model": "professional_realtime_flow_ai",
            }

        return {
            **base_payload,
            "decision": chosen["action"],
            "action": chosen["action"],
            "score": int(IntradaySignalEngine._clamp(chosen["score"], 0, 100)),
            "title": "專業即時結構 AI 訊號",
            "reason": f"{chosen['action']} 分數 {chosen['score']}，扣成本期望 {chosen['expected_value']}%。",
            "reasons": [
                f"{chosen['action']} 結構分數 {chosen['score']}，估計勝率 {chosen['win_rate']}%，需求 {required}%",
                f"扣成本後期望 {chosen['expected_value']}%｜動態停損 {eff_stop}%｜動態停利 {eff_take}%",
                *(chosen.get("reasons", [])[:4]),
                *(common_reasons[:5]),
                *(chosen.get("penalties", [])[:3]),
            ],
            "risk_level": "NORMAL",
            "model": "professional_realtime_flow_ai",
        }

    @staticmethod
    def _wait(reason):
        return {
            "decision": "WAIT",
            "action": "WAIT",
            "score": 30,
            "title": "等待確認",
            "reason": reason,
            "reasons": [reason],
            "buy": {},
            "sell": {},
            "chosen": {},
            "required_win_rate": 0,
            "risk_level": "HIGH",
        }
