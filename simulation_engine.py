import math
import random
from datetime import datetime, timedelta


class SimulationEngine:
    STOCK_BASE = {
        "2330": {
            "name": "台積電",
            "price": 2340.0,
            "tick": 5.0,
            "base_volume": 360,
        },
        "3481": {
            "name": "群創",
            "price": 65.0,
            "tick": 0.05,
            "base_volume": 520,
        },
        "2317": {
            "name": "鴻海",
            "price": 210.0,
            "tick": 0.5,
            "base_volume": 420,
        },
        "2454": {
            "name": "聯發科",
            "price": 1360.0,
            "tick": 5.0,
            "base_volume": 260,
        },
    }

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _round_to_tick(price, tick_size):
        if tick_size <= 0:
            return round(price, 2)

        return round(round(price / tick_size) * tick_size, 2)

    @staticmethod
    def _stock_profile(stock_code):
        code = str(stock_code)

        if code in SimulationEngine.STOCK_BASE:
            return SimulationEngine.STOCK_BASE[code]

        return {
            "name": code,
            "price": 100.0,
            "tick": 0.1,
            "base_volume": 300,
        }

    @staticmethod
    def _scenario_step(scenario, i, n):
        x = i / max(n - 1, 1)

        if scenario in ["漲停鎖死"]:
            return 0.22 + max(0, 0.35 - x) * 0.18

        if scenario in ["跌停鎖死"]:
            return -0.22 - max(0, 0.35 - x) * 0.18

        if scenario in ["跳空急跌"]:
            if x < 0.16:
                return -0.62
            if x < 0.48:
                return -0.14
            return 0.05

        if scenario in ["軋空行情", "誘空嘎空"]:
            if x < 0.22:
                return -0.08
            if x < 0.58:
                return 0.27
            return 0.11

        if scenario in ["誘多出貨", "拉高出貨"]:
            if x < 0.35:
                return 0.22
            if x < 0.58:
                return 0.02
            return -0.18

        if scenario in ["主力吸籌"]:
            if x < 0.45:
                return 0.00
            if x < 0.72:
                return 0.07
            return 0.15

        return 0.035 * math.sin(x * math.pi * 6)

    @staticmethod
    def _make_intraday_history(stock_code, tick=0, scenario="一般波動"):
        profile = SimulationEngine._stock_profile(stock_code)

        name = profile["name"]
        base_price = float(profile["price"])
        tick_size = float(profile["tick"])
        base_volume = float(profile["base_volume"])

        tick = SimulationEngine._safe_int(tick, 0)

        # 重要：seed 不要包含 tick，這樣每次刷新前面的歷史不會亂跳
        seed = (
            sum(ord(c) for c in str(stock_code))
            + sum(ord(c) for c in str(scenario)) * 7
        )

        rng = random.Random(seed)

        # 模擬盤一開始就給足日內資料，之後每次刷新逐步增加
        point_count = min(
            240,
            max(90, 90 + tick * 3),
        )

        start = datetime.now().replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )

        history = []

        open_gap = rng.uniform(-0.006, 0.006)

        if scenario in ["跳空急跌"]:
            open_gap = rng.uniform(-0.025, -0.012)

        elif scenario in ["軋空行情", "誘空嘎空"]:
            open_gap = rng.uniform(-0.012, 0.002)

        elif scenario in ["漲停鎖死"]:
            open_gap = rng.uniform(0.018, 0.035)

        elif scenario in ["跌停鎖死"]:
            open_gap = rng.uniform(-0.035, -0.018)

        last_price = base_price * (1 + open_gap)

        day_high = last_price
        day_low = last_price

        cum_amount = 0.0
        cum_volume = 0.0

        for i in range(point_count):
            x = i / max(point_count - 1, 1)

            trend_force = SimulationEngine._scenario_step(
                scenario=scenario,
                i=i,
                n=point_count,
            )

            wave = math.sin(x * math.pi * 7) * 0.09
            micro_wave = math.sin(x * math.pi * 31) * 0.026
            noise = rng.uniform(-0.075, 0.075)

            price_scale = max(base_price * 0.0012, tick_size)

            change = (
                trend_force
                + wave
                + micro_wave
                + noise
            ) * price_scale

            last_price = last_price + change

            limit_high = base_price * 1.095
            limit_low = base_price * 0.905

            last_price = max(
                limit_low,
                min(limit_high, last_price),
            )

            price = SimulationEngine._round_to_tick(
                last_price,
                tick_size,
            )

            day_high = max(day_high, price)
            day_low = min(day_low, price)

            open_factor = 1.9 if i < 12 else 1.0
            volatility_factor = 1 + abs(change) / max(tick_size, 0.01) * 0.32
            wave_volume = 1 + max(0, math.sin(x * math.pi * 5)) * 0.8

            spike = 1.0

            if i in [18, 45, 72, 108, 145, 185]:
                spike = rng.uniform(2.1, 4.0)

            volume = (
                base_volume
                * open_factor
                * volatility_factor
                * wave_volume
                * spike
                * rng.uniform(0.65, 1.35)
            )

            volume = max(10, round(volume, 0))

            cum_amount += price * volume
            cum_volume += volume

            vwap = cum_amount / max(cum_volume, 1)

            event = ""

            if i >= 1:
                prev = history[-1]

                if price > vwap and prev["price"] <= prev["vwap"]:
                    event = "BUY_CROSS_VWAP"

                elif price < vwap and prev["price"] >= prev["vwap"]:
                    event = "SELL_CROSS_VWAP"

            history.append(
                {
                    "time": start + timedelta(minutes=i),
                    "price": price,
                    "volume": volume,
                    "vwap": round(vwap, 2),
                    "high": round(day_high, 2),
                    "low": round(day_low, 2),
                    "event": event,
                }
            )

        latest = history[-1]

        bid_bias = 1.0
        ask_bias = 1.0

        if latest["price"] >= latest["vwap"]:
            bid_bias = 1.24
            ask_bias = 0.92
        else:
            bid_bias = 0.92
            ask_bias = 1.24

        bids = []
        asks = []

        for level in range(5):
            step = tick_size * (level + 1)

            bid_price = SimulationEngine._round_to_tick(
                latest["price"] - step,
                tick_size,
            )

            ask_price = SimulationEngine._round_to_tick(
                latest["price"] + step,
                tick_size,
            )

            bid_size = round(
                base_volume * bid_bias * rng.uniform(0.55, 1.65),
                0,
            )

            ask_size = round(
                base_volume * ask_bias * rng.uniform(0.55, 1.65),
                0,
            )

            bids.append(
                {
                    "price": bid_price,
                    "size": bid_size,
                }
            )

            asks.append(
                {
                    "price": ask_price,
                    "size": ask_size,
                }
            )

        quote = {
            "name": name,
            "stock_code": str(stock_code),
            "price": latest["price"],
            "vwap": latest["vwap"],
            "avgPrice": latest["vwap"],
            "last_size": latest["volume"],
            "lastSize": latest["volume"],
            "volume": latest["volume"],
            "high": latest["high"],
            "low": latest["low"],
            "bids": bids,
            "asks": asks,
            "trade": {
                "serial": f"SIM_{stock_code}_{tick}_{point_count}",
                "time": latest["time"].isoformat(),
                "price": latest["price"],
                "size": latest["volume"],
            },
            "serial": f"SIM_{stock_code}_{tick}_{point_count}",
            "history": history,
            "scenario": scenario,
        }

        return quote

    @staticmethod
    def get_quote(stock_code="2330", tick=0, scenario="一般波動", **kwargs):
        return SimulationEngine._make_intraday_history(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario or "一般波動",
        )

    @staticmethod
    def generate(stock_code="2330", tick=0, scenario="一般波動", **kwargs):
        return SimulationEngine.get_quote(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario,
        )

    @staticmethod
    def get_market_data(stock_code="2330", tick=0, scenario="一般波動", **kwargs):
        return SimulationEngine.get_quote(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario,
        )

    @staticmethod
    def next_quote(stock_code="2330", tick=0, scenario="一般波動", **kwargs):
        return SimulationEngine.get_quote(
            stock_code=stock_code,
            tick=tick,
            scenario=scenario,
        )
