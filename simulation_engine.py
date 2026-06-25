# simulation_engine.py

import random


class SimulationEngine:

    def __init__(self, mode="一般波動", base_price=100):
        self.mode = mode
        self.base_price = base_price

    def generate(self, tick, total_ticks):

        progress = tick / max(total_ticks, 1)

        price = self.base_price

        if self.mode == "漲停鎖死":

            if progress < 0.25:
                price += progress * 40
            else:
                price = round(self.base_price * 1.10, 2)

        elif self.mode == "跌停鎖死":

            if progress < 0.25:
                price -= progress * 40
            else:
                price = round(self.base_price * 0.90, 2)

        elif self.mode == "跳空急跌":

            if progress < 0.15:
                price = self.base_price
            else:
                price = self.base_price - 15

        elif self.mode == "軋空行情":

            if progress < 0.35:
                price -= progress * 15
            else:
                price += (progress - 0.35) * 35

        elif self.mode == "誘多出貨":

            if progress < 0.5:
                price += progress * 20
            else:
                price += 10 - (progress - 0.5) * 35

        elif self.mode == "誘空嘎空":

            if progress < 0.4:
                price -= progress * 15
            else:
                price -= 6
                price += (progress - 0.4) * 40

        elif self.mode == "拉高出貨":

            if progress < 0.3:
                price += progress * 50

            elif progress < 0.6:
                price += 15 + random.uniform(-1, 1)

            else:
                price += 15
                price -= (progress - 0.6) * 45

        elif self.mode == "主力吸籌":

            price += random.uniform(-0.2, 0.2)

        else:

            if progress < 0.33:
                price += progress * 15

            elif progress < 0.66:
                price += 5
                price -= (progress - 0.33) * 20

            else:
                price -= 2
                price += (progress - 0.66) * 12

        price = round(price, 2)

        bids = [
            {
                "price": round(price - 0.5 - i * 0.5, 2),
                "size": random.randint(100, 1500),
            }
            for i in range(5)
        ]

        asks = [
            {
                "price": round(price + 0.5 + i * 0.5, 2),
                "size": random.randint(100, 1500),
            }
            for i in range(5)
        ]

        if self.mode == "漲停鎖死":
            bids[0]["size"] = 8000
            asks = []

        if self.mode == "跌停鎖死":
            asks[0]["size"] = 8000
            bids[0]["size"] = 50

        trade_size = random.randint(50, 500)

return {
    "name": f"模擬-{self.mode}",
    "price": price,
    "open": self.base_price,
    "high": max(price, self.base_price),
    "low": min(price, self.base_price),
    "vwap": self.base_price,
    "last_size": trade_size,
    "bids": bids,
    "asks": asks,
    "trade": {
        "price": price,
        "size": trade_size,
    },
    "is_close": False,
}
