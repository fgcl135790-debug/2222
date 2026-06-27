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
    def _avg(values):
        nums = []

        for v in values:
            n = DecisionEngine._safe_float(v, None)

            if n is not None and n > 0:
                nums.append(n)

        if not nums:
            return 0

        return sum(nums) / len(nums)

    @staticmethod
    def _detect_fake_break(price, vwap, prices, volumes):
        """
        假突破 / 假跌破偵測邏輯：

        假突破：
        - 價格突破近期高點
        - 但成交量沒有放大
        - 或突破後仍貼近 VWAP，代表沒有有效脫離成本區

        假跌破：
        - 價格跌破近期低點
        - 但成交量沒有放大
        - 或跌破後仍貼近 VWAP，代表殺盤不乾脆
        """

        price = DecisionEngine._safe_float(price)
        vwap = DecisionEngine._safe_float(vwap)

        if prices is None or len(prices) < 8:
            return {
                "fake_signal": "NONE",
                "fake_text": "資料不足，暫不判斷假突破",
                "fake_level": 0,
            }

        clean_prices = [
            DecisionEngine._safe_float(p)
            for p in prices
            if DecisionEngine._safe_float(p) > 0
        ]

        if len(clean_prices) < 8:
            return {
                "fake_signal": "NONE",
                "fake_text": "價格資料不足，暫不判斷假突破",
                "fake_level": 0,
            }

        history = clean_prices[:-1]

        if len(history) < 5:
            return {
                "fake_signal": "NONE",
                "fake_text": "歷史資料不足，暫不判斷假突破",
                "fake_level": 0,
            }

        lookback = history[-20:]

        recent_high = max(lookback)
        recent_low = min(lookback)

        recent_range = max(
            recent_high - recent_low,
            price * 0.001,
        )

        break_buffer = max(
            price * 0.001,
            recent_range * 0.12,
        )

        current_volume = 0

        if volumes:
            current_volume = DecisionEngine._safe_float(volumes[-1])

        prev_volumes = []

        if volumes and len(volumes) >= 2:
            prev_volumes = volumes[-21:-1]

        avg_volume = DecisionEngine._avg(prev_volumes)

        weak_volume = False

        if avg_volume > 0 and current_volume > 0:
            weak_volume = current_volume < avg_volume * 1.2

        near_vwap = False

        if vwap > 0:
            near_vwap = abs(price - vwap) / vwap <= 0.003

        is_breakout = price > recent_high + break_buffer
        is_breakdown = price < recent_low - break_buffer

        if is_breakout:

            if weak_volume or near_vwap:

                return {
                    "fake_signal": "FAKE_BREAKOUT",
                    "fake_text": "疑似假突破：突破近期高點，但量能不足或未有效脫離 VWAP",
                    "fake_level": 2 if weak_volume and near_vwap else 1,
                }

            return {
                "fake_signal": "REAL_BREAKOUT",
                "fake_text": "有效突破：價格突破近期高點，且未出現明顯假突破條件",
                "fake_level": 0,
            }

        if is_breakdown:

            if weak_volume or near_vwap:

                return {
                    "fake_signal": "FAKE_BREAKDOWN",
                    "fake_text": "疑似假跌破：跌破近期低點，但量能不足或仍貼近 VWAP",
                    "fake_level": 2 if weak_volume and near_vwap else 1,
                }

            return {
                "fake_signal": "REAL_BREAKDOWN",
                "fake_text": "有效跌破：價格跌破近期低點，且未出現明顯假跌破條件",
                "fake_level": 0,
            }

        return {
            "fake_signal": "NONE",
            "fake_text": "未出現明顯突破或跌破",
            "fake_level": 0,
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
        prices=None,
        volumes=None,
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
        # 五檔主力力道
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
        # 假突破 / 假跌破偵測
        # =========================

        fake = DecisionEngine._detect_fake_break(
            price=price,
            vwap=vwap,
            prices=prices,
            volumes=volumes,
        )

        fake_signal = fake["fake_signal"]
        fake_text = fake["fake_text"]
        fake_level = fake["fake_level"]

        if fake_signal == "FAKE_BREAKOUT":

            long_score -= 4
            short_score += 2

            reasons.append(fake_text)
            reasons.append("策略：疑似假突破，不建議追多")

        elif fake_signal == "FAKE_BREAKDOWN":

            short_score -= 4
            long_score += 2

            reasons.append(fake_text)
            reasons.append("策略：疑似假跌破，不建議追空")

        elif fake_signal == "REAL_BREAKOUT":

            long_score += 2

            reasons.append(fake_text)
            reasons.append("策略：有效突破，可偏多觀察")

        elif fake_signal == "REAL_BREAKDOWN":

            short_score += 2

            reasons.append(fake_text)
            reasons.append("策略：有效跌破，可偏空觀察")

        else:

            reasons.append(fake_text)

        # =========================
        # 決策分數
        # =========================

        bias = long_score - short_score

        confidence = 50 + abs(bias) * 6

        if ai_score >= 70:
            confidence += 8

        elif ai_score <= 40:
            confidence -= 8

        if fake_signal in ["FAKE_BREAKOUT", "FAKE_BREAKDOWN"]:
            confidence -= fake_level * 8

        confidence = int(
            DecisionEngine._clamp(confidence)
        )

        # =========================
        # 交易決策
        # =========================

        block_long = fake_signal == "FAKE_BREAKOUT"
        block_short = fake_signal == "FAKE_BREAKDOWN"

        if bias >= 4 and confidence >= 60 and not block_long:

            action = "BUY"

            entry_low = round(price * 0.998, 2)
            entry_high = round(price * 1.002, 2)

            stop_loss = round(price * 0.994, 2)
            take_profit = round(price * 1.012, 2)

            risk_value = price - stop_loss
            reward_value = take_profit - price

            rr = round(
                reward_value / risk_value,
                2,
            ) if risk_value > 0 else "-"

            entry = f"{entry_low} ~ {entry_high}"

            reasons.append("V7.5 決策：多方條件成立")
            reasons.append("策略：回測進場區再考慮做多，避免追高")

        elif bias <= -4 and confidence >= 60 and not block_short:

            action = "SELL"

            entry_low = round(price * 0.998, 2)
            entry_high = round(price * 1.002, 2)

            stop_loss = round(price * 1.006, 2)
            take_profit = round(price * 0.988, 2)

            risk_value = stop_loss - price
            reward_value = price - take_profit

            rr = round(
                reward_value / risk_value,
                2,
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

            if block_long:
                reasons.append("V7.5 決策：假突破風險，暫停做多")

            elif block_short:
                reasons.append("V7.5 決策：假跌破風險，暫停做空")

            else:
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

            "fake_signal": fake_signal,

            "fake_text": fake_text,

            "fake_level": fake_level,

            "reasons": reasons,

        }

