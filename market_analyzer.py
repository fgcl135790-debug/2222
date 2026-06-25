# market_analyzer.py

import pandas as pd


class MarketAnalyzer:

    # =========================
    # EMA
    # =========================

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

    # =========================
    # 趨勢判斷
    # =========================

    @staticmethod
    def trend(
        price,
        vwap,
        ema5,
        ema20,
    ):

        if price > vwap and ema5 > ema20:
            return "多頭"

        if price < vwap and ema5 < ema20:
            return "空頭"

        return "盤整"

    # =========================
    # AI交易判斷
    # =========================

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

            score += 30

            reasons.append(
                "現價站上VWAP"
            )

        else:

            score -= 30

            reasons.append(
                "現價跌破VWAP"
            )

        # EMA5

        if ema5 > ema20:

            score += 25

            reasons.append(
                "EMA5突破EMA20"
            )

        else:

            score -= 25

            reasons.append(
                "EMA5跌破EMA20"
            )

        # EMA20

        if ema20 > ema60:

            score += 20

            reasons.append(
                "EMA20站上EMA60"
            )

        else:

            score -= 20

            reasons.append(
                "EMA20跌破EMA60"
            )

        # 買賣盤力道

        bid_ratio = (
            total_bid /
            max(total_ask, 1)
        )

        if bid_ratio > 1.5:

            score += 25

            reasons.append(
                "委買明顯大於委賣"
            )

        elif bid_ratio > 1:

            score += 10

            reasons.append(
                "委買略強"
            )

        elif bid_ratio < 0.67:

            score -= 25

            reasons.append(
                "委賣明顯大於委買"
            )

        else:

            score -= 10

            reasons.append(
                "委賣略強"
            )

        confidence = min(
            abs(score),
            100
        )

        if score >= 40:

            action = "做多"

        elif score <= -40:

            action = "做空"

        else:

            action = "觀望"

        return (
            action,
            confidence,
            reasons
        )

    # =========================
    # 主力分數
    # =========================

    @staticmethod
    def institution_score(
        total_bid,
        total_ask,
    ):

        total = (
            total_bid +
            total_ask
        )

        if total == 0:
            return 50

        return int(
            total_bid /
            total *
            100
        )

    # =========================
    # 主力吸籌
    # =========================

    @staticmethod
    def detect_accumulation(
        total_bid,
        total_ask,
    ):

        return (
            total_bid >
            total_ask * 2
        )

    # =========================
    # 主力出貨
    # =========================

    @staticmethod
    def detect_distribution(
        total_bid,
        total_ask,
    ):

        return (
            total_ask >
            total_bid * 2
        )

    # =========================
    # 多頭排列
    # =========================

    @staticmethod
    def bullish_alignment(
        ema5,
        ema20,
        ema60,
    ):

        return (
            ema5 >
            ema20 >
            ema60
        )

    # =========================
    # 空頭排列
    # =========================

    @staticmethod
    def bearish_alignment(
        ema5,
        ema20,
        ema60,
    ):

        return (
            ema5 <
            ema20 <
            ema60
        )

    # =========================
    # 軋空行情
    # =========================

    @staticmethod
    def detect_short_squeeze(
        price_change,
        volume,
    ):

        return (
            price_change > 5
            and
            volume > 1500
        )

    # =========================
    # 拉高出貨
    # =========================

    @staticmethod
    def detect_distribution_spike(
        price_change,
        volume,
    ):

        return (
            price_change > 3
            and
            volume > 2000
        )

    # =========================
    # 跌停風險
    # =========================

    @staticmethod
    def limit_down_risk(
        price,
        vwap,
        total_bid,
        total_ask,
    ):

        if (
            price < vwap
            and
            total_ask >
            total_bid * 3
        ):
            return True

        return False

    # =========================
    # 漲停機率
    # =========================

    @staticmethod
    def limit_up_probability(
        price,
        vwap,
        total_bid,
        total_ask,
    ):

        score = 0

        if price > vwap:
            score += 40

        if total_bid > total_ask:
            score += 30

        ratio = (
            total_bid /
            max(total_ask, 1)
        )

        if ratio > 2:
            score += 30

        return min(
            score,
            100
        )
