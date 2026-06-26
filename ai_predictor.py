import numpy as np


class AIPredictor:

    # =========================
    # AI 綜合評分 v4
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

        score = 50

        reasons = []

        # =====================
        # VWAP（加入緩衝）
        # =====================

        vwap_gap = price - vwap

        if vwap_gap >= 0.30:

            score += 10

            reasons.append("站穩VWAP")

        elif vwap_gap >= 0:

            score += 4

            reasons.append("VWAP上方")

        elif vwap_gap <= -0.30:

            score -= 10

            reasons.append("跌破VWAP")

        else:

            score -= 4

            reasons.append("VWAP下方")

        # =====================
        # EMA（加入Gap）
        # =====================

        ema_gap = ema5 - ema20

        if ema_gap >= 0.10:

            score += 10

            reasons.append("EMA5明顯突破EMA20")

        elif ema_gap >= 0:

            score += 4

            reasons.append("EMA5略強")

        elif ema_gap <= -0.10:

            score -= 10

            reasons.append("EMA5跌破EMA20")

        else:

            score -= 4

            reasons.append("EMA5略弱")

        if ema20 > ema60:

            score += 8

            reasons.append("中期均線多頭")

        else:

            score -= 8

            reasons.append("中期均線空頭")

        # =====================
        # RSI（降低敏感度）
        # =====================

        if rsi <= 25:

            score += 15

            reasons.append("RSI極度超賣")

        elif rsi <= 35:

            score += 8

            reasons.append("RSI超賣")

        elif 45 <= rsi <= 60:

            score += 5

            reasons.append("RSI健康")

        elif 60 < rsi <= 70:

            score += 2

            reasons.append("RSI偏強")

        elif 70 < rsi <= 80:

            score -= 8

            reasons.append("RSI過熱")

        else:

            score -= 15

            reasons.append("RSI極度超買")

        # =====================
        # MACD（加入Gap）
        # =====================

        macd_gap = macd - macd_signal

        if macd_gap >= 0.05:

            score += 12

            reasons.append("MACD黃金交叉")

        elif macd_gap >= 0:

            score += 4

            reasons.append("MACD略偏多")

        elif macd_gap <= -0.05:

            score -= 12

            reasons.append("MACD死亡交叉")

        else:

            score -= 4

            reasons.append("MACD略偏空")

        # =====================
        # MACD Histogram
        # =====================

        if macd_hist >= 0.10:

            score += 6

            reasons.append("紅柱放大")

        elif macd_hist > 0:

            score += 2

            reasons.append("紅柱")

        elif macd_hist <= -0.10:

            score -= 6

            reasons.append("綠柱放大")

        else:

            score -= 2

            reasons.append("綠柱")

        # =====================
        # Momentum（降低敏感度）
        # =====================

        if momentum >= 3:

            score += 10

            reasons.append("Momentum強勢")

        elif momentum >= 1:

            score += 5

            reasons.append("Momentum偏強")

        elif momentum <= -3:

            score -= 10

            reasons.append("Momentum轉弱")

        elif momentum <= -1:

            score -= 5

            reasons.append("Momentum偏空")

        else:

            reasons.append("Momentum中性")

        # =====================
        # 委買委賣（AI v4）
        # =====================

        bid_ratio = total_bid / max(total_ask, 1)

        if bid_ratio >= 3:

            score += 20

            reasons.append("委買極強")

        elif bid_ratio >= 2:

            score += 15

            reasons.append("委買強勢")

        elif bid_ratio >= 1.5:

            score += 10

            reasons.append("委買偏強")

        elif bid_ratio >= 1.2:

            score += 4

            reasons.append("委買略優")

        elif 0.9 <= bid_ratio <= 1.1:

            reasons.append("買賣均衡")

        elif bid_ratio <= 0.4:

            score -= 20

            reasons.append("委賣極強")

        elif bid_ratio <= 0.6:

            score -= 15

            reasons.append("委賣強勢")

        elif bid_ratio <= 0.8:

            score -= 8

            reasons.append("委賣偏強")

        else:

            score -= 3

            reasons.append("委賣略優")

        # =====================
        # 成交量趨勢
        # =====================

        if volume_trend == "UP":

            score += 8

            reasons.append("成交量放大")

        elif volume_trend == "DOWN":

            score -= 8

            reasons.append("成交量萎縮")

        else:

            reasons.append("成交量持平")

        # =====================
        # 波動率
        # =====================

        if volatility >= 5:

            score += 6

            reasons.append("波動擴大")

        elif volatility >= 3:

            score += 3

            reasons.append("波動增加")

        elif volatility <= 0.5:

            score -= 4

            reasons.append("波動過低")

        # =====================
        # AI 分數限制
        # =====================

        score = int(max(0, min(score, 100)))
        # =====================
        # AI 建議（台股版）
        # =====================

        confidence = score

        if score >= 90:

            action = "🔥🔴 強烈做多"

        elif score >= 75:

            action = "🔴 做多"

        elif score >= 60:

            action = "🟡 偏多"

        elif 45 <= score < 60:

            action = "⚪ 觀望"

        elif score >= 25:

            action = "🟢 偏空"

        else:

            action = "🔥🟢 強烈做空"

        # =====================
        # AI 信心修正
        # =====================

        if 45 <= score <= 55:

            confidence = max(confidence - 5, 0)

            reasons.append("多空尚未明朗")

        elif score >= 80:

            confidence = min(confidence + 5, 100)

            reasons.append("多頭訊號一致")

        elif score <= 20:

            confidence = min(confidence + 5, 100)

            reasons.append("空頭訊號一致")

        return (

            action,

            confidence,

            reasons,

        )

    # =========================
    # AI 趨勢反轉預測 v4
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

        if len(prices) < 10:

            return (

                "NONE",

                "⚪ AI資料不足",

                0,

                "⭐",

                ["等待更多成交資料"],

            )

        score = 50

        reasons = []

        # =====================
        # 最近5筆價格確認
        # =====================

        last5 = prices[-5:]

        up_count = 0
        down_count = 0

        for i in range(1, len(last5)):

            if last5[i] > last5[i - 1]:

                up_count += 1

            elif last5[i] < last5[i - 1]:

                down_count += 1

        if up_count >= 4:

            score += 15
            reasons.append("價格連續走高")

        elif up_count == 3:

            score += 8
            reasons.append("價格開始轉強")

        elif down_count >= 4:

            score -= 15
            reasons.append("價格連續走弱")

        elif down_count == 3:

            score -= 8
            reasons.append("價格開始轉弱")

        else:

            reasons.append("價格整理")

        # =====================
        # VWAP
        # =====================

        if price > vwap:

            score += 8
            reasons.append("站穩VWAP")

        else:

            score -= 8
            reasons.append("跌破VWAP")

        # =====================
        # EMA
        # =====================

        if ema5 > ema20 > ema60:

            score += 15
            reasons.append("均線多頭排列")

        elif ema5 > ema20:

            score += 8
            reasons.append("短均線翻多")

        elif ema5 < ema20 < ema60:

            score -= 15
            reasons.append("均線空頭排列")

        elif ema5 < ema20:

            score -= 8
            reasons.append("短均線翻空")

        # =====================
        # RSI
        # =====================

        if rsi <= 30:

            score += 10
            reasons.append("RSI超賣")

        elif rsi >= 70:

            score -= 10
            reasons.append("RSI超買")

        elif 45 <= rsi <= 60:

            score += 5
            reasons.append("RSI健康")

        # =====================
        # MACD
        # =====================

        gap = macd - macd_signal

        if gap >= 0.05:

            score += 12
            reasons.append("MACD黃金交叉")

        elif gap <= -0.05:

            score -= 12
            reasons.append("MACD死亡交叉")

        # =====================
        # Momentum
        # =====================

        if momentum >= 3:

            score += 10
            reasons.append("Momentum強勢")

        elif momentum >= 1:

            score += 5
            reasons.append("Momentum轉強")

        elif momentum <= -3:

            score -= 10
            reasons.append("Momentum轉弱")

        elif momentum <= -1:

            score -= 5
            reasons.append("Momentum偏空")

        # =====================
        # 委買委賣
        # =====================

        bid_ratio = total_bid / max(total_ask, 1)

        if bid_ratio >= 2:

            score += 15
            reasons.append("委買強勢")

        elif bid_ratio >= 1.5:

            score += 8
            reasons.append("買盤增加")

        elif bid_ratio <= 0.5:

            score -= 15
            reasons.append("委賣強勢")

        elif bid_ratio <= 0.8:

            score -= 8
            reasons.append("賣盤增加")

        # =====================
        # 限制
        # =====================

        probability = int(max(0, min(score, 100)))

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
        # AI訊號（加入緩衝）
        # =====================

        if probability >= 85:

            signal = "BUY"

            text = "🔴 AI判斷：高機率反轉向上"

        elif probability >= 70:

            signal = "WATCH"

            text = "🟡 AI判斷：有反轉跡象"

        elif probability <= 20:

            signal = "SELL"

            text = "🟢 AI判斷：高機率持續下跌"

        elif probability <= 35:

            signal = "WATCH"

            text = "🟡 AI判斷：偏空觀察"

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
