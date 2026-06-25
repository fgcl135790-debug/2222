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
