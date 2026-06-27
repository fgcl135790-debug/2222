import math
import random
from datetime import datetime, timedelta


class SimulationEngine:
    STOCK_BASE = {
        "2330": {
            "name": "台積電",
            "price": 2340.0,
            "tick": 5.0,
            "base_volume": 320,
        },
        "3481": {
            "name": "群創",
            "price": 65.0,
            "tick": 0.05,
            "base_volume": 420,
        },
        "2317": {
            "name": "鴻海",
            "price": 210.0,
            "tick": 0.5,
            "base_volume": 360,
        },
        "2454": {
            "name": "聯發科",
            "price": 1360.0,
            "tick": 5.0,
            "base_volume": 220,
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
            "base_volume": 260,
        }

    @staticmethod
    def _scenario_step(scenario, i, n):
        """
        回傳每一分鐘的趨勢推力。
        正數偏多，負數偏空。
        """

        x = i / max(n - 1, 1)

        if scenario in ["漲停鎖死"]:
            return 0.18 + max(0, 0.35 - x) * 0.12

        if scenario in ["跌停鎖死"]:
            return -0.18 - max(0, 0.35 - x) * 0.12

        if scenario in ["跳空急跌"]:
            if x < 0.15:
                return -0.55
            if x < 0.45:
                return -0.15
            return 0.05

        if scenario in ["軋空行情", "誘空嘎空"]:
            if x < 0.25:
                return -0.08
            if x < 0.55:
                return 0.25
            return 0.13

        if scenario in ["誘多出貨", "拉高出貨"]:
            if x < 0.32:
                return 0.22
            if x < 0.58:
                return 0.03
            return -0.18

        if scenario in ["主力吸籌"]:
            if x < 0.45:
                return 0.01
            if x < 0.75:
                return 0.08
            return 0.16

        if scenario in ["多空震盪", "一般波動"]:
            return 0.03 * math.sin(x * math.pi * 6)

        return 0.02 * math.sin(x * math.pi * 5)

    @staticmethod
    def _make_intraday_history(stock_code, tick=0, scenario="一般波動"):
        profile = SimulationEngine._stock_profile(stock_code)

        name = profile["name"]
        base_price = float(profile["price"])
        tick_size = float(profile["tick"])
        base_volume = float(profile["base_volume"])

        tick = SimulationEngine._safe_int(tick, 0)

        seed = sum(ord(c) for c in str(stock_code)) + tick * 17 + sum(ord(c) for c in str(scenario))
        rng = random.Random(seed)

        # 模擬目前已經走到盤中某一段。
        # 初始就給 80 筆以上，避免 K 線只有 1~2 根。
        point_count = min(240, max(80, 80 + tick * 2))

        start = datetime.now().replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )

        history = []

        last_price = base_price
        cum_amount = 0.0
        cum_volume = 0.0

        open_gap = rng.uniform(-0.006, 0.006)

        if scenario in ["跳空急跌"]:
            open_gap = rng.uniform(-0.025, -0.012)

        elif scenario in ["軋空行情", "誘空嘎空"]:
            open_gap = rng.uniform(-0.01, 0.003)

        elif scenario in ["漲停鎖死"]:
            open_gap = rng.uniform(0.018, 0.035)

        elif scenario in ["跌停鎖死"]:
            open_gap = rng.uniform(-0.035, -0.018)

        last_price = base_price * (1 + open_gap)

        day_high = last_price
        day_low = last_price

        for i in range(point_count):
            x = i / max(point_count - 1, 1)

            trend_force = SimulationEngine._scenario_step(
                scenario=scenario,
                i=i,
                n=point_count,
            )

            wave = math.sin(x * math.pi * 7) * 0.08
            micro_wave = math.sin(x * math.pi * 31) * 0.025
            noise = rng.uniform(-0.08, 0.08)

            # 價格越高，單點波動金額越大
            price_scale = max(base_price * 0.0012, tick_size)

            change = (trend_force + wave + micro_wave + noise) * price_scale
            last_price = last_price + change

            # 不讓模擬走太誇張
            limit_high = base_price * 1.095
            limit_low = base_price * 0.905
            last_price = max(limit_low, min(limit_high, last_price))

            price = SimulationEngine._round_to_tick(last_price, tick_size)

            day_high = max(day_high, price)
            day_low = min(day_low, price)

            # 量能：開盤大、波動大、突破時放大
            open_factor = 1.8 if i < 12 else 1.0
            volatility_factor = 1 + abs(change) / max(tick_size, 0.01) * 0.35
            wave_volume = 1 + max(0, math.sin(x * math.pi * 5)) * 0.75

            spike = 1.0
            if i in [20, 45, 70, 105, 145, 185]:
                spike = rng.uniform(2.2, 4.2)

            volume = base_volume * open_factor * volatility_factor * wave_volume * spike
            volume = max(10, volume * rng.uniform(0.65, 1.35))
            volume = round(volume, 0)

            cum_amount += price * volume
            cum_volume += volume
            vwap = cum_amount / max(cum_volume, 1)

            event = ""

            if i >= 2:
                prev = history[-1]["price"]

                if price > vwap and prev <= history[-1]["vwap"]:
                    event = "BUY_CROSS_VWAP"

                elif price < vwap and prev >= history[-1]["vwap"]:
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
            bid_bias = 1.25
            ask_bias = 0.92
        else:
            bid_bias = 0.92
            ask_bias = 1.25

        bids = []
        asks = []

        for level in range(5):
            step = tick_size * (level + 1)

            bid_price = SimulationEngine._round_to_tick(latest["price"] - step, tick_size)
            ask_price = SimulationEngine._round_to_tick(latest["price"] + step, tick_size)

            bid_size = round(base_volume * bid_bias * rng.uniform(0.55, 1.65), 0)
            ask_size = round(base_volume * ask_bias * rng.uniform(0.55, 1.65), 0)

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
