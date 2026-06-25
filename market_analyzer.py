# market_analyzer.py

import pandas as pd


class MarketAnalyzer:

    @staticmethod
    def calculate_ema(prices, span):

        if len(prices) == 0:
            return 0

        return (
            pd.Series(prices)
            .ewm(span=span)
            .mean()
            .iloc[-1]
        )

    @staticmethod
    def trend(price, vwap, ema5, ema20):

        if price > vwap and ema5 > ema20:
            return "多頭"

        if price < vwap and ema5 < ema20:
            return "空頭"

        return "盤整"

    @staticmethod
    def detect_accumulation(
        price_range,
        avg_volume,
    ):

        if price_range < 0.5 and avg_volume > 1000:
            return True

        return False

    @staticmethod
    def detect_distribution(
        price_change,
        volume,
    ):

        if price_change < -2 and volume > 1000:
            return True

        return False

    @staticmethod
    def detect_short_squeeze(
        price_change,
        volume,
    ):

        if price_change > 5 and volume > 1500:
            return True

        return False
    @staticmethod
    def trading_signal(
        price,
        vwap,
        ema5,
        ema20,
        ema60,
        total_bid,
        total_ask,
    ):

        score = 0
        reasons = []

        # VWAP
        if price > vwap:
            score += 25
            reasons.append("現價站上VWAP")
        else:
            score -= 25
            reasons.append("現價跌破VWAP")

        # EMA5 / EMA20
        if ema5 > ema20:
            score += 20
            reasons.append("EMA5 > EMA20")
        else:
            score -= 20
            reasons.append("EMA5 < EMA20")

        # EMA20 / EMA60
        if ema20 > ema60:
            score += 20
            reasons.append("EMA20 > EMA60")
        else:
            score -= 20
            reasons.append("EMA20 < EMA60")

        # 買賣力道
        if total_bid > total_ask:
            score += 15
            reasons.append("委買大於委賣")
        else:
            score -= 15
            reasons.append("委賣大於委買")

        confidence = min(abs(score), 100)

        if score >= 20:
            action = "做多"

        elif score <= -20:
            action = "做空"

        else:
            action = "觀望"

        return action, confidence, reasons
