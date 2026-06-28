import pandas as pd
import numpy as np


class IntradayLabelEngine:
    """
    把 1分K 轉成當沖訓練標籤。

    每一根K都測兩種候選：
    BUY  : 未來 max_hold_bars 根K，先碰停利還是先碰停損
    SELL : 未來 max_hold_bars 根K，先碰停利還是先碰停損

    停損停利用價格本身，不含手續費。
    成本只扣在 pnl_pct。
    """

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
    def _ema(series, span):
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def _rsi(close, period=14):
        diff = close.diff()
        gain = diff.clip(lower=0)
        loss = (-diff).clip(lower=0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        return rsi.fillna(50)

    @staticmethod
    def _add_indicators(df):
        df = df.copy()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.sort_values("date").reset_index(drop=True)

        df["trade_date"] = df["date"].dt.strftime("%Y-%m-%d")
        df["time"] = df["date"].dt.strftime("%H:%M")
        df["minute_index"] = df.groupby("trade_date").cumcount()

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["open", "high", "low", "close"])

        frames = []

        for trade_date, day in df.groupby("trade_date"):
            day = day.copy().reset_index(drop=True)

            day["ema5"] = IntradayLabelEngine._ema(day["close"], 5)
            day["ema20"] = IntradayLabelEngine._ema(day["close"], 20)
            day["ema60"] = IntradayLabelEngine._ema(day["close"], 60)

            amount = day["close"] * day["volume"].fillna(0)
            volume_sum = day["volume"].fillna(0).cumsum().replace(0, np.nan)
            day["vwap"] = amount.cumsum() / volume_sum
            day["vwap"] = day["vwap"].fillna(day["close"])

            ema12 = IntradayLabelEngine._ema(day["close"], 12)
            ema26 = IntradayLabelEngine._ema(day["close"], 26)
            day["macd"] = ema12 - ema26
            day["macd_signal"] = IntradayLabelEngine._ema(day["macd"], 9)
            day["macd_hist"] = day["macd"] - day["macd_signal"]

            day["rsi"] = IntradayLabelEngine._rsi(day["close"], 14)

            day["slope_3"] = day["close"].pct_change(3) * 100
            day["slope_5"] = day["close"].pct_change(5) * 100
            day["slope_10"] = day["close"].pct_change(10) * 100
            day["slope_20"] = day["close"].pct_change(20) * 100

            day["volume_ma20"] = day["volume"].rolling(20).mean()
            day["volume_ratio"] = day["volume"] / day["volume_ma20"].replace(0, np.nan)
            day["volume_ratio"] = day["volume_ratio"].fillna(1.0)

            day["high_30"] = day["high"].rolling(30).max()
            day["low_30"] = day["low"].rolling(30).min()
            day["high_60"] = day["high"].rolling(60).max()
            day["low_60"] = day["low"].rolling(60).min()

            day["high_30"] = day["high_30"].fillna(day["high"].expanding().max())
            day["low_30"] = day["low_30"].fillna(day["low"].expanding().min())
            day["high_60"] = day["high_60"].fillna(day["high"].expanding().max())
            day["low_60"] = day["low_60"].fillna(day["low"].expanding().min())

            day["vwap_gap"] = (day["close"] - day["vwap"]) / day["vwap"].replace(0, np.nan) * 100
            day["ema_gap"] = (day["ema5"] - day["ema20"]) / day["ema20"].replace(0, np.nan) * 100

            day["distance_to_high_30"] = (day["high_30"] - day["close"]) / day["close"].replace(0, np.nan) * 100
            day["distance_to_low_30"] = (day["close"] - day["low_30"]) / day["close"].replace(0, np.nan) * 100
            day["distance_to_high_60"] = (day["high_60"] - day["close"]) / day["close"].replace(0, np.nan) * 100
            day["distance_to_low_60"] = (day["close"] - day["low_60"]) / day["close"].replace(0, np.nan) * 100

            day["open_gap"] = (day["close"] - day["open"].iloc[0]) / day["open"].iloc[0] * 100
            day["day_range_pct"] = (day["high"].expanding().max() - day["low"].expanding().min()) / day["close"] * 100

            frames.append(day)

        if not frames:
            return pd.DataFrame()

        out = pd.concat(frames, ignore_index=True)
        out = out.replace([np.inf, -np.inf], np.nan)
        out = out.fillna(0)

        return out

    @staticmethod
    def _time_bucket(minute_index):
        minute_index = int(minute_index)

        if minute_index < 15:
            return "09:00-09:14"
        if minute_index < 30:
            return "09:15-09:29"
        if minute_index < 60:
            return "09:30-09:59"
        if minute_index < 90:
            return "10:00-10:29"
        if minute_index < 150:
            return "10:30-11:29"
        if minute_index < 210:
            return "11:30-12:29"

        return "12:30-13:30"

    @staticmethod
    def _vwap_zone(vwap_gap):
        v = IntradayLabelEngine._safe_float(vwap_gap)

        if v >= 1.0:
            return "ABOVE_1"
        if v >= 0.4:
            return "ABOVE_04"
        if v >= 0.05:
            return "ABOVE_SMALL"
        if v > -0.05:
            return "NEAR"
        if v > -0.4:
            return "BELOW_SMALL"
        if v > -1.0:
            return "BELOW_04"

        return "BELOW_1"

    @staticmethod
    def _slope_zone(slope):
        s = IntradayLabelEngine._safe_float(slope)

        if s >= 0.8:
            return "UP_STRONG"
        if s >= 0.25:
            return "UP"
        if s > -0.25:
            return "FLAT"
        if s > -0.8:
            return "DOWN"

        return "DOWN_STRONG"

    @staticmethod
    def _simulate_trade(
        day,
        entry_idx,
        action,
        stop_pct=0.6,
        take_pct=2.0,
        max_hold_bars=50,
        cost_pct=0.435,
    ):
        entry_row = day.iloc[entry_idx]
        entry_price = IntradayLabelEngine._safe_float(entry_row["close"])

        if entry_price <= 0:
            return None

        stop_rate = stop_pct / 100
        take_rate = take_pct / 100

        if action == "BUY":
            stop_price = entry_price * (1 - stop_rate)
            take_price = entry_price * (1 + take_rate)
        else:
            stop_price = entry_price * (1 + stop_rate)
            take_price = entry_price * (1 - take_rate)

        exit_price = entry_price
        exit_time = entry_row["date"]
        exit_reason = "時間出場"
        hold_bars = 0

        last_idx = min(len(day) - 1, entry_idx + max_hold_bars)

        for i in range(entry_idx + 1, last_idx + 1):
            row = day.iloc[i]
            high = IntradayLabelEngine._safe_float(row["high"])
            low = IntradayLabelEngine._safe_float(row["low"])
            close = IntradayLabelEngine._safe_float(row["close"])

            hold_bars = i - entry_idx
            exit_time = row["date"]

            if action == "BUY":
                hit_stop = low <= stop_price
                hit_take = high >= take_price

                if hit_stop and hit_take:
                    exit_price = stop_price
                    exit_reason = "停損"
                    break

                if hit_take:
                    exit_price = take_price
                    exit_reason = "停利"
                    break

                if hit_stop:
                    exit_price = stop_price
                    exit_reason = "停損"
                    break

                exit_price = close

            else:
                hit_stop = high >= stop_price
                hit_take = low <= take_price

                if hit_stop and hit_take:
                    exit_price = stop_price
                    exit_reason = "停損"
                    break

                if hit_take:
                    exit_price = take_price
                    exit_reason = "停利"
                    break

                if hit_stop:
                    exit_price = stop_price
                    exit_reason = "停損"
                    break

                exit_price = close

        if action == "BUY":
            gross_pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            gross_pnl_pct = (entry_price - exit_price) / entry_price * 100

        pnl_pct = gross_pnl_pct - cost_pct

        if exit_reason == "停利":
            label = "WIN"
        elif exit_reason == "停損":
            label = "LOSS"
        else:
            label = "TIME_WIN" if pnl_pct > 0 else "TIME_LOSS"

        return {
            "action": action,
            "entry_time": entry_row["date"],
            "entry_price": round(entry_price, 2),
            "exit_time": exit_time,
            "exit_price": round(exit_price, 2),
            "exit_reason": exit_reason,
            "hold_bars": hold_bars,
            "stop_price": round(stop_price, 2),
            "take_price": round(take_price, 2),
            "gross_pnl_pct": round(gross_pnl_pct, 3),
            "cost_pct": round(cost_pct, 3),
            "pnl_pct": round(pnl_pct, 3),
            "label": label,
            "is_win": 1 if pnl_pct > 0 else 0,
        }

    @staticmethod
    def build_labels(
        kline_df,
        stop_pct=0.6,
        take_pct=2.0,
        max_hold_bars=50,
        cost_pct=0.435,
        start_minute=15,
        end_minute=250,
    ):
        df = IntradayLabelEngine._add_indicators(kline_df)

        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        rows = []

        feature_cols = [
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

        for trade_date, day in df.groupby("trade_date"):
            day = day.copy().reset_index(drop=True)

            if len(day) < start_minute + max_hold_bars + 5:
                continue

            last_entry_idx = min(len(day) - max_hold_bars - 1, end_minute)

            for i in range(start_minute, last_entry_idx):
                base = day.iloc[i]

                for action in ["BUY", "SELL"]:
                    sim = IntradayLabelEngine._simulate_trade(
                        day=day,
                        entry_idx=i,
                        action=action,
                        stop_pct=stop_pct,
                        take_pct=take_pct,
                        max_hold_bars=max_hold_bars,
                        cost_pct=cost_pct,
                    )

                    if not sim:
                        continue

                    row = {
                        "trade_date": trade_date,
                        "time": base["time"],
                        "minute_index": int(base["minute_index"]),
                        "time_bucket": IntradayLabelEngine._time_bucket(base["minute_index"]),
                        "vwap_zone": IntradayLabelEngine._vwap_zone(base["vwap_gap"]),
                        "slope_zone": IntradayLabelEngine._slope_zone(base["slope_10"]),
                    }

                    for col in feature_cols:
                        row[col] = round(IntradayLabelEngine._safe_float(base[col]), 5)

                    row.update(sim)
                    rows.append(row)

        labels = pd.DataFrame(rows)

        if labels.empty:
            return df, labels

        labels = labels.sort_values(["entry_time", "action"]).reset_index(drop=True)

        return df, labels

    @staticmethod
    def extract_current_features(
        prices,
        volumes,
        now_time=None,
    ):
        """
        從目前盤中價格序列抽出即時特徵。
        DecisionEngine 會用這個特徵丟進模型預測。
        """

        if prices is None:
            prices = []

        if volumes is None:
            volumes = []

        df = pd.DataFrame({
            "close": prices,
            "volume": volumes if len(volumes) == len(prices) else [1] * len(prices),
        })

        if df.empty or len(df) < 35:
            return None

        df["open"] = df["close"]
        df["high"] = df["close"]
        df["low"] = df["close"]

        if now_time is None:
            base_time = pd.Timestamp("2026-01-01 09:00:00")
            df["date"] = [base_time + pd.Timedelta(minutes=i) for i in range(len(df))]
        else:
            base_day = pd.Timestamp(now_time).strftime("%Y-%m-%d")
            base_time = pd.Timestamp(f"{base_day} 09:00:00")
            df["date"] = [base_time + pd.Timedelta(minutes=i) for i in range(len(df))]

        enriched = IntradayLabelEngine._add_indicators(df)

        if enriched.empty:
            return None

        row = enriched.iloc[-1]

        feature = {
            "minute_index": int(row["minute_index"]),
            "time_bucket": IntradayLabelEngine._time_bucket(row["minute_index"]),
            "vwap_zone": IntradayLabelEngine._vwap_zone(row["vwap_gap"]),
            "slope_zone": IntradayLabelEngine._slope_zone(row["slope_10"]),
            "vwap_gap": IntradayLabelEngine._safe_float(row["vwap_gap"]),
            "ema_gap": IntradayLabelEngine._safe_float(row["ema_gap"]),
            "rsi": IntradayLabelEngine._safe_float(row["rsi"]),
            "macd_hist": IntradayLabelEngine._safe_float(row["macd_hist"]),
            "slope_3": IntradayLabelEngine._safe_float(row["slope_3"]),
            "slope_5": IntradayLabelEngine._safe_float(row["slope_5"]),
            "slope_10": IntradayLabelEngine._safe_float(row["slope_10"]),
            "slope_20": IntradayLabelEngine._safe_float(row["slope_20"]),
            "volume_ratio": IntradayLabelEngine._safe_float(row["volume_ratio"], 1.0),
            "distance_to_high_30": IntradayLabelEngine._safe_float(row["distance_to_high_30"]),
            "distance_to_low_30": IntradayLabelEngine._safe_float(row["distance_to_low_30"]),
            "distance_to_high_60": IntradayLabelEngine._safe_float(row["distance_to_high_60"]),
            "distance_to_low_60": IntradayLabelEngine._safe_float(row["distance_to_low_60"]),
            "open_gap": IntradayLabelEngine._safe_float(row["open_gap"]),
            "day_range_pct": IntradayLabelEngine._safe_float(row["day_range_pct"]),
        }

        return feature
