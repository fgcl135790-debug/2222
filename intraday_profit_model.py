import pandas as pd
import numpy as np


class IntradayProfitModel:
    """
    成本感知的相似 K 線當沖模型。

    核心概念：
    - 先用歷史 1 分 K 依照固定停損 / 停利 / 持有 K 數做標籤。
    - 盤中把當下特徵拿去找相似樣本。
    - 不只看勝率，也看扣完成本後的期望報酬 expected_value。
    - 若扣成本後期望值 <= 0，或勝率低於該停損停利組合的損益兩平勝率，就回傳 WAIT。
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

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            if pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def required_win_rate_pct(stop_pct=0.6, take_pct=2.0, cost_pct=0.435, safety_margin=4.0):
        """
        計算扣成本後的最低損益兩平勝率。
        win_net  = 停利% - 成本%
        loss_net = 停損% + 成本%
        break_even = loss_net / (win_net + loss_net)
        """
        stop_pct = IntradayProfitModel._safe_float(stop_pct, 0.6)
        take_pct = IntradayProfitModel._safe_float(take_pct, 2.0)
        cost_pct = IntradayProfitModel._safe_float(cost_pct, 0.435)
        safety_margin = IntradayProfitModel._safe_float(safety_margin, 4.0)

        win_net = take_pct - cost_pct
        loss_net = stop_pct + cost_pct

        if win_net <= 0:
            return 99.0

        breakeven = loss_net / max(win_net + loss_net, 0.000001) * 100
        return round(min(95.0, breakeven + safety_margin), 2)

    def _distance_score(self, df, feature):
        dist = pd.Series(0.0, index=df.index)

        # 越重要的特徵權重越高。重點放在「剛起動」與「離 VWAP / 高低點的位置」。
        weights = {
            "vwap_gap": 1.45,
            "ema_gap": 1.05,
            "rsi": 0.85,
            "macd_hist": 1.15,
            "slope_3": 1.50,
            "slope_5": 1.30,
            "slope_10": 1.35,
            "slope_20": 0.90,
            "volume_ratio": 0.85,
            "distance_to_high_30": 1.20,
            "distance_to_low_30": 1.20,
            "distance_to_high_60": 0.75,
            "distance_to_low_60": 0.75,
            "open_gap": 0.90,
            "day_range_pct": 0.75,
        }

        for col in self.FEATURE_COLS:
            if col not in df.columns:
                continue

            stat = self.feature_stats.get(col, {"std": 1.0})
            std = max(stat.get("std", 1.0), 0.000001)
            weight = weights.get(col, 1.0)
            target = self._safe_float(feature.get(col), 0.0)

            dist += ((df[col] - target).abs() / std) * weight

        return dist

    def _summarize(self, sample, action, feature, level):
        if sample.empty:
            return {
                "action": action,
                "level": level,
                "sample_count": 0,
                "win_rate": 0.0,
                "loss_rate": 0.0,
                "time_rate": 0.0,
                "avg_pnl_pct": -999.0,
                "median_pnl_pct": -999.0,
                "expected_value": -999.0,
                "profit_factor": 0.0,
                "best_time_bucket": "",
                "reason": "沒有相似樣本",
            }

        sample = sample.copy()
        wins = sample[sample["pnl_pct"] > 0]
        losses = sample[sample["pnl_pct"] <= 0]
        time_exits = sample[sample.get("exit_reason", "") == "時間出場"] if "exit_reason" in sample.columns else pd.DataFrame()

        win_rate = len(wins) / len(sample) * 100
        loss_rate = len(losses) / len(sample) * 100
        time_rate = len(time_exits) / len(sample) * 100 if len(sample) else 0

        avg_pnl = float(sample["pnl_pct"].mean())
        median_pnl = float(sample["pnl_pct"].median())

        gross_win = float(wins["pnl_pct"].sum()) if not wins.empty else 0.0
        gross_loss = abs(float(losses["pnl_pct"].sum())) if not losses.empty else 0.0

        if gross_loss <= 0:
            profit_factor = 99.0 if gross_win > 0 else 0.0
        else:
            profit_factor = gross_win / gross_loss

        reason = (
            f"{level} 相似樣本 {len(sample)} 筆，"
            f"勝率 {win_rate:.1f}%，"
            f"扣成本期望 {avg_pnl:.3f}%"
        )

        return {
            "action": action,
            "level": level,
            "sample_count": int(len(sample)),
            "win_rate": round(win_rate, 2),
            "loss_rate": round(loss_rate, 2),
            "time_rate": round(time_rate, 2),
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
                loose = df[df["time_bucket"] == time_bucket].copy()

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

    def predict(
        self,
        feature,
        min_expected_value=0.10,
        min_win_rate=None,
        min_sample_count=25,
        stop_pct=0.6,
        take_pct=2.0,
        cost_pct=0.435,
        safety_margin=4.0,
    ):
        buy = self.predict_action(feature, "BUY")
        sell = self.predict_action(feature, "SELL")

        required_win_rate = self.required_win_rate_pct(
            stop_pct=stop_pct,
            take_pct=take_pct,
            cost_pct=cost_pct,
            safety_margin=safety_margin,
        )

        if min_win_rate is not None:
            required_win_rate = max(required_win_rate, self._safe_float(min_win_rate, required_win_rate))

        # edge 是排序用；是否放行仍以「扣成本期望 > 0」與「勝率高於損益兩平」為主。
        buy_edge = (
            buy["expected_value"] * 20
            + (buy["win_rate"] - required_win_rate) * 0.70
            + min(buy["sample_count"], 120) * 0.03
            + min(buy["profit_factor"], 5) * 3
        )

        sell_edge = (
            sell["expected_value"] * 20
            + (sell["win_rate"] - required_win_rate) * 0.70
            + min(sell["sample_count"], 120) * 0.03
            + min(sell["profit_factor"], 5) * 3
        )

        buy["edge"] = round(buy_edge, 2)
        sell["edge"] = round(sell_edge, 2)
        buy["required_win_rate"] = required_win_rate
        sell["required_win_rate"] = required_win_rate
        buy["min_expected_value"] = min_expected_value
        sell["min_expected_value"] = min_expected_value

        allow_buy = (
            buy["expected_value"] >= min_expected_value
            and buy["win_rate"] >= required_win_rate
            and buy["sample_count"] >= min_sample_count
            and buy["profit_factor"] >= 1.05
        )

        allow_sell = (
            sell["expected_value"] >= min_expected_value
            and sell["win_rate"] >= required_win_rate
            and sell["sample_count"] >= min_sample_count
            and sell["profit_factor"] >= 1.05
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

        if decision == "WAIT":
            risk_level = "HIGH"
            reason = (
                "扣成本後期望值不足，或勝率未高於此停損停利組合的損益兩平勝率，"
                "此筆交易風險高，暫不出手。"
            )
            score = max(0, min(70, int(45 + max(buy_edge, sell_edge) * 0.5)))
        else:
            risk_level = "NORMAL"
            reason = chosen.get("reason", "")
            score = (
                55
                + max(0, chosen["expected_value"]) * 18
                + max(0, chosen["win_rate"] - required_win_rate) * 0.75
                + min(chosen["profit_factor"], 3) * 4
            )
            score = int(self._clamp(score, 50, 100))

        return {
            "decision": decision,
            "score": score,
            "buy": buy,
            "sell": sell,
            "chosen": chosen,
            "reason": reason,
            "risk_level": risk_level,
            "required_win_rate": required_win_rate,
            "min_expected_value": min_expected_value,
            "stop_pct": round(self._safe_float(stop_pct, 0.6), 3),
            "take_pct": round(self._safe_float(take_pct, 2.0), 3),
            "cost_pct": round(self._safe_float(cost_pct, 0.435), 3),
        }
