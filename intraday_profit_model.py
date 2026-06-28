import pandas as pd
import numpy as np


class IntradayProfitModel:
    """
    用歷史標籤資料做相似情境預測。

    不是機器學習套件，先用穩定的相似樣本法：
    1. 先找同方向 BUY / SELL
    2. 優先找同時間區間、同 VWAP 區、同斜率區
    3. 再用數值特徵距離找最像的樣本
    4. 算勝率、平均報酬、期望值
    """

    FEATURE_COLS = [
        "vwap_gap",
        "ema_gap",
        "rsi",
        "macd_hist",
        "slope_3",
        "slope_5",
        "slope_10",
        "slope_20",
        "volume_ratio",
        "distance_to_high_30",
        "distance_to_low_30",
        "distance_to_high_60",
        "distance_to_low_60",
        "open_gap",
        "day_range_pct",
    ]

    def __init__(self, labels_df):
        self.labels = labels_df.copy() if labels_df is not None else pd.DataFrame()

        if not self.labels.empty:
            self.labels = self.labels.replace([np.inf, -np.inf], np.nan)
            self.labels = self.labels.fillna(0)

        self.feature_stats = self._build_feature_stats()

    def _build_feature_stats(self):
        if self.labels.empty:
            return {}

        stats = {}

        for col in self.FEATURE_COLS:
            if col not in self.labels.columns:
                continue

            std = float(self.labels[col].std())

            if std <= 0 or np.isnan(std):
                std = 1.0

            stats[col] = {
                "mean": float(self.labels[col].mean()),
                "std": std,
            }

        return stats

    def _safe_float(self, value, default=0.0):
        try:
            if value is None:
                return default
            if pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    def _distance_score(self, df, feature):
        dist = pd.Series(0.0, index=df.index)

        weights = {
            "vwap_gap": 1.4,
            "ema_gap": 1.0,
            "rsi": 0.8,
            "macd_hist": 1.1,
            "slope_3": 1.4,
            "slope_5": 1.2,
            "slope_10": 1.3,
            "slope_20": 0.8,
            "volume_ratio": 0.8,
            "distance_to_high_30": 1.1,
            "distance_to_low_30": 1.1,
            "distance_to_high_60": 0.7,
            "distance_to_low_60": 0.7,
            "open_gap": 0.8,
            "day_range_pct": 0.7,
        }

        for col in self.FEATURE_COLS:
            if col not in df.columns:
                continue

            stat = self.feature_stats.get(col, {"std": 1.0})
            std = stat.get("std", 1.0)
            weight = weights.get(col, 1.0)
            target = self._safe_float(feature.get(col), 0.0)

            dist += ((df[col] - target).abs() / max(std, 0.000001)) * weight

        return dist

    def _summarize(self, sample, action, feature, level):
        if sample.empty:
            return {
                "action": action,
                "level": level,
                "sample_count": 0,
                "win_rate": 0.0,
                "avg_pnl_pct": -999,
                "median_pnl_pct": -999,
                "expected_value": -999,
                "profit_factor": 0.0,
                "best_time_bucket": "",
                "reason": "沒有相似樣本",
            }

        wins = sample[sample["pnl_pct"] > 0]
        losses = sample[sample["pnl_pct"] <= 0]

        win_rate = len(wins) / len(sample) * 100
        avg_pnl = float(sample["pnl_pct"].mean())
        median_pnl = float(sample["pnl_pct"].median())

        gross_win = wins["pnl_pct"].sum() if not wins.empty else 0.0
        gross_loss = abs(losses["pnl_pct"].sum()) if not losses.empty else 0.0

        if gross_loss <= 0:
            profit_factor = 99.0 if gross_win > 0 else 0.0
        else:
            profit_factor = gross_win / gross_loss

        reason = (
            f"{level} 相似樣本 {len(sample)} 筆，"
            f"勝率 {win_rate:.1f}%，"
            f"平均報酬 {avg_pnl:.3f}%"
        )

        return {
            "action": action,
            "level": level,
            "sample_count": int(len(sample)),
            "win_rate": round(win_rate, 2),
            "avg_pnl_pct": round(avg_pnl, 3),
            "median_pnl_pct": round(median_pnl, 3),
            "expected_value": round(avg_pnl, 3),
            "profit_factor": round(profit_factor, 2),
            "best_time_bucket": str(feature.get("time_bucket", "")),
            "reason": reason,
        }

    def predict_action(self, feature, action, top_n=120):
        if self.labels.empty:
            return self._summarize(pd.DataFrame(), action, feature, "EMPTY")

        df = self.labels[self.labels["action"] == action].copy()

        if df.empty:
            return self._summarize(pd.DataFrame(), action, feature, "NO_ACTION")

        time_bucket = feature.get("time_bucket")
        vwap_zone = feature.get("vwap_zone")
        slope_zone = feature.get("slope_zone")

        strict = df[
            (df["time_bucket"] == time_bucket)
            & (df["vwap_zone"] == vwap_zone)
            & (df["slope_zone"] == slope_zone)
        ].copy()

        if len(strict) >= 25:
            candidate = strict
            level = "STRICT"
        else:
            medium = df[
                (df["time_bucket"] == time_bucket)
                & (df["slope_zone"] == slope_zone)
            ].copy()

            if len(medium) >= 35:
                candidate = medium
                level = "MEDIUM"
            else:
                loose = df[
                    (df["time_bucket"] == time_bucket)
                ].copy()

                if len(loose) >= 50:
                    candidate = loose
                    level = "TIME_ONLY"
                else:
                    candidate = df.copy()
                    level = "ALL"

        if candidate.empty:
            return self._summarize(pd.DataFrame(), action, feature, level)

        candidate["distance"] = self._distance_score(candidate, feature)
        sample = candidate.sort_values("distance").head(top_n).copy()

        return self._summarize(sample, action, feature, level)

    def predict(self, feature, min_expected_value=0.05, min_win_rate=45.0):
        buy = self.predict_action(feature, "BUY")
        sell = self.predict_action(feature, "SELL")

        buy_edge = (
            buy["expected_value"] * 12
            + buy["win_rate"] * 0.45
            + min(buy["sample_count"], 120) * 0.03
            + buy["profit_factor"] * 2
        )

        sell_edge = (
            sell["expected_value"] * 12
            + sell["win_rate"] * 0.45
            + min(sell["sample_count"], 120) * 0.03
            + sell["profit_factor"] * 2
        )

        buy["edge"] = round(buy_edge, 2)
        sell["edge"] = round(sell_edge, 2)

        allow_buy = (
            buy["expected_value"] >= min_expected_value
            and buy["win_rate"] >= min_win_rate
            and buy["sample_count"] >= 20
        )

        allow_sell = (
            sell["expected_value"] >= min_expected_value
            and sell["win_rate"] >= min_win_rate
            and sell["sample_count"] >= 20
        )

        if allow_buy and buy_edge >= sell_edge:
            decision = "BUY"
            chosen = buy
        elif allow_sell and sell_edge > buy_edge:
            decision = "SELL"
            chosen = sell
        else:
            decision = "WAIT"
            chosen = buy if buy_edge >= sell_edge else sell

        score = 50

        if decision != "WAIT":
            score = (
                50
                + max(0, chosen["expected_value"]) * 12
                + max(0, chosen["win_rate"] - 45) * 0.8
                + min(chosen["profit_factor"], 3) * 5
            )

        score = int(max(0, min(100, score)))

        return {
            "decision": decision,
            "score": score,
            "buy": buy,
            "sell": sell,
            "chosen": chosen,
            "reason": chosen.get("reason", ""),
        }
