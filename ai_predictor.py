import numpy as np


class AIPredictor:

    # =========================
    # AI 綜合評分 v5
    # =========================

    @staticmethod
    def score(

        price,

        vwap,

        ema5,

        ema20,

        ema60,

        rsi,

        macd,

        macd_signal,

        macd_hist,

        total_bid,

        total_ask,

        momentum,

        volume_trend,

        volatility,

    ):

        ai_score = 50

        reasons = []

        # =====================
        # VWAP（降低敏感度）
        # =====================

        vwap_gap = price - vwap

        if vwap_gap >= 0.5:

            ai_score += 10

            reasons.append("站穩VWAP")

        elif vwap_gap >= 0:

            ai_score += 5

            reasons.append("略高於VWAP")

        elif vwap_gap <= -0.5:

            ai_score -= 10

            reasons.append("跌破VWAP")

        else:

            ai_score -= 5

            reasons.append("略低於VWAP")

        # =====================
        # EMA
        # =====================

        if ema5 > ema20 > ema60:

            ai_score += 20

            reasons.append("均線多頭排列")

        elif ema5 > ema20:

            ai_score += 10

            reasons.append("短均線翻多")

        elif ema5 < ema20 < ema60:

            ai_score -= 20

            reasons.append("均線空頭排列")

        elif ema5 < ema20:

            ai_score -= 10

            reasons.append("短均線翻空")

        # =====================
        # RSI
        # =====================

        if rsi <= 30:

            ai_score += 15

            reasons.append("RSI超賣")

        elif rsi <= 40:

            ai_score += 8

            reasons.append("RSI偏低")

        elif 45 <= rsi <= 60:

            ai_score += 5

            reasons.append("RSI健康")

        elif rsi >= 70:

            ai_score -= 15

            reasons.append("RSI超買")

        elif rsi >= 60:

            ai_score -= 8

            reasons.append("RSI偏高")

        # =====================
        # MACD
        # =====================

        macd_gap = macd - macd_signal

        if macd_gap >= 0.10:

            ai_score += 12

            reasons.append("MACD黃金交叉")

        elif macd_gap >= 0:

            ai_score += 6

            reasons.append("MACD翻多")

        elif macd_gap <= -0.10:

            ai_score -= 12

            reasons.append("MACD死亡交叉")

        else:

            ai_score -= 6

            reasons.append("MACD翻空")

        # =====================
        # MACD Histogram
        # =====================

        if macd_hist >= 0.15:

            ai_score += 6

            reasons.append("紅柱放大")

        elif macd_hist > 0:

            ai_score += 3

            reasons.append("紅柱")

        elif macd_hist <= -0.15:

            ai_score -= 6

            reasons.append("綠柱放大")

        else:

            ai_score -= 3

            reasons.append("綠柱")

        # =====================
        # Momentum（加入緩衝）
        # =====================

        if momentum >= 4:

            ai_score += 12

            reasons.append("Momentum強勢")

        elif momentum >= 2:

            ai_score += 6

            reasons.append("Momentum轉強")

        elif momentum <= -4:

            ai_score -= 12

            reasons.append("Momentum轉弱")

        elif momentum <= -2:

            ai_score -= 6

            reasons.append("Momentum偏空")

        else:

            reasons.append("Momentum整理")

        # =====================
        # 委買委賣
        # =====================

        bid_ratio = total_bid / max(total_ask, 1)

        if bid_ratio >= 2.5:

            ai_score += 20

            reasons.append("委買極強")

        elif bid_ratio >= 2:

            ai_score += 15

            reasons.append("委買強勢")

        elif bid_ratio >= 1.3:

            ai_score += 8

            reasons.append("委買略強")

        elif bid_ratio <= 0.4:

            ai_score -= 20

            reasons.append("委賣極強")

        elif bid_ratio <= 0.7:

            ai_score -= 15

            reasons.append("委賣強勢")

        elif bid_ratio <= 0.9:

            ai_score -= 8

            reasons.append("委賣略強")

        else:

            reasons.append("買賣力道平衡")

        # =====================
        # 成交量
        # =====================

        if volume_trend == "UP":

            ai_score += 10

            reasons.append("成交量放大")

        elif volume_trend == "DOWN":

            ai_score -= 8

            reasons.append("成交量萎縮")

        else:

            reasons.append("成交量持平")

        # =====================
        # 波動率
        # =====================

        if volatility >= 5:

            ai_score += 8

            reasons.append("波動率放大")

        elif volatility >= 3:

            ai_score += 4

            reasons.append("波動增加")

        elif volatility <= 0.5:

            ai_score -= 5

            reasons.append("波動過低")

        # =====================
        # AI分數限制
        # =====================

        ai_score = int(

            max(

                0,

                min(ai_score, 100)

            )

        )

        confidence = ai_score

        # =====================
        # AI建議（台股配色）
        # =====================

        if ai_score >= 90:

            action = "🔥🔴 強烈做多"

        elif ai_score >= 75:

            action = "🔴 做多"

        elif ai_score >= 60:

            action = "🟡 偏多"

        elif ai_score >= 40:

            action = "⚪ 觀望"

        elif ai_score >= 25:

            action = "🟡 偏空"

        else:

            action = "🔥🟢 強烈做空"

        return (

            action,

            confidence,

            reasons,

        )

    # =========================
    # AI 趨勢反轉預測 v5
    # =========================

    @staticmethod
    def predict_reversal(

        price,

        prices,

        vwap,

        ema5,

        ema20,

        ema60,

        rsi,

        macd,

        macd_signal,

        total_bid,

        total_ask,

        momentum,

    ):

        score = 50

        reasons = []

        # =====================
        # VWAP
        # =====================

        if price > vwap * 1.002:

            score += 10

            reasons.append("站穩VWAP")

        elif price < vwap * 0.998:

            score -= 10

            reasons.append("跌破VWAP")

        # =====================
        # EMA
        # =====================

        if ema5 > ema20 > ema60:

            score += 15

            reasons.append("均線多頭排列")

        elif ema5 < ema20 < ema60:

            score -= 15

            reasons.append("均線空頭排列")

        # =====================
        # RSI
        # =====================

        if rsi <= 30:

            score += 10

            reasons.append("RSI超賣")

        elif rsi >= 70:

            score -= 10

            reasons.append("RSI超買")

        # =====================
        # MACD
        # =====================

        gap = macd - macd_signal

        if gap >= 0.15:

            score += 12

            reasons.append("MACD黃金交叉")

        elif gap <= -0.15:

            score -= 12

            reasons.append("MACD死亡交叉")

        # =====================
        # Momentum
        # =====================

        if momentum >= 4:

            score += 10

            reasons.append("Momentum強勢")

        elif momentum <= -4:

            score -= 10

            reasons.append("Momentum轉弱")

        # =====================
        # 最近5筆價格
        # =====================

        if len(prices) >= 5:

            last5 = prices[-5:]

            rise = 0

            fall = 0

            for i in range(1, len(last5)):

                if last5[i] > last5[i-1]:

                    rise += 1

                elif last5[i] < last5[i-1]:

                    fall += 1

            if rise >= 4:

                score += 12

                reasons.append("價格持續走高")

            elif fall >= 4:

                score -= 12

                reasons.append("價格持續走弱")

        # =====================
        # 委買委賣
        # =====================

        bid_ratio = total_bid / max(total_ask, 1)

        if bid_ratio >= 2:

            score += 12

            reasons.append("委買強勢")

        elif bid_ratio <= 0.6:

            score -= 12

            reasons.append("委賣強勢")

        # =====================
        # 分數限制
        # =====================

        probability = int(

            max(

                0,

                min(score, 100)

            )

        )

        # =====================
        # 星等
        # =====================

        if probability >= 90:

            stars = "⭐⭐⭐⭐⭐"

        elif probability >= 80:

            stars = "⭐⭐⭐⭐"

        elif probability >= 65:

            stars = "⭐⭐⭐"

        elif probability >= 50:

            stars = "⭐⭐"

        else:

            stars = "⭐"

        # =====================
        # AI訊號（台股配色）
        # =====================

        if probability >= 85:

            signal = "BUY"

            text = "🔴 AI判斷：高機率反轉向上"

        elif probability >= 70:

            signal = "WATCH"

            text = "🟡 AI判斷：持續觀察"

        elif probability <= 20:

            signal = "SELL"

            text = "🟢 AI判斷：持續轉弱"

        else:

            signal = "NONE"

            text = "⚪ AI判斷：方向未明"

        return (

            signal,

            text,

            probability,

            stars,

            reasons,

        )

        # =====================
        # AI 修正（避免過度敏感）
        # =====================

        # 多頭排列且站上VWAP，再增加信心
        if ema5 > ema20 > ema60 and price > vwap:

            probability = min(probability + 5, 100)

            reasons.append("多頭趨勢確認")

        # 空頭排列且跌破VWAP，再降低信心
        elif ema5 < ema20 < ema60 and price < vwap:

            probability = max(probability - 5, 0)

            reasons.append("空頭趨勢確認")

        # Momentum 與 MACD 同方向才增加可信度
        if momentum > 3 and macd > macd_signal:

            probability = min(probability + 3, 100)

            reasons.append("動能同步轉強")

        elif momentum < -3 and macd < macd_signal:

            probability = max(probability - 3, 0)

            reasons.append("動能同步轉弱")

        # 最後再次限制範圍
        probability = int(

            max(

                0,

                min(probability, 100)

            )

        )

        return (

            signal,

            text,

            probability,

            stars,

            reasons,

        )
