import random

class SimulationEngine:

    def __init__(self, mode="一般波動", base_price=100):
        self.mode = mode
        self.base_price = float(base_price)
        self.price = float(base_price)

    def generate(self, tick, duration):

        drift = 0

        if self.mode == "一般波動":
            drift = random.uniform(-0.3, 0.3)

        elif self.mode == "軋空行情":
            drift = random.uniform(0.2, 1.2)

        elif self.mode == "誘空嘎空":
            drift = random.uniform(-0.2, 1.5)

        elif self.mode == "主力吸籌":
            drift = random.uniform(-0.1, 0.8)

        else:
            drift = random.uniform(-0.5, 0.5)

        # 🔥 修復：避免 float explode / None
        self.price = max(1, self.price + drift)

        price = round(self.price, 2)

        volume = random.randint(50, 3000)

        bids = [{"price": price - i*0.1, "size": random.randint(10, 500)} for i in range(5)]
        asks = [{"price": price + i*0.1, "size": random.randint(10, 500)} for i in range(5)]

        return {
            "name": "SIM STOCK",
            "price": price,
            "vwap": price + random.uniform(-0.2, 0.2),
            "last_size": volume,
            "bids": bids,
            "asks": asks,
            "trade": {"serial": tick},
            "is_close": False
        }
