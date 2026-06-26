import random
import math
from datetime import datetime


class SimulationEngine:
    """
    V4.5 Professional Market Simulation Engine
    - trend + volatility + randomness
    - scenario control
    - stable output (no crash)
    """

    def __init__(self, mode="一般波動", base_price=100):
        self.mode = mode
        self.base_price = float(base_price)
        self.last_price = float(base_price)

        self.step = 0

        # 波動參數（核心）
        self.volatility = 0.3
        self.trend_bias = 0.0

        # 不同情境
        self._set_mode(mode)

    # =========================
    # 模式設定
    # =========================
    def _set_mode(self, mode):

        if mode == "一般波動":
            self.volatility = 0.3
            self.trend_bias = 0.0

        elif mode == "軋空行情":
            self.volatility = 0.6
            self.trend_bias = 0.15

        elif mode == "出貨":
            self.volatility = 0.5
            self.trend_bias = -0.2

        elif mode == "吸籌":
            self.volatility = 0.25
            self.trend_bias = 0.05

        elif mode == "誘多出貨":
            self.volatility = 0.4
            self.trend_bias = -0.1

        else:
            self.volatility = 0.3
            self.trend_bias = 0.0

    # =========================
    # 核心價格生成（重點）
    # =========================
    def _generate_change(self):

        # sine 趨勢（市場節奏）
        cycle = math.sin(self.step / 8)

        # 隨機噪音
        noise = random.uniform(-1, 1)

        # 波動 + 趨勢 + 噪音
        change = (
            cycle * self.trend_bias * 2 +
            noise * self.volatility
        )

        # 防呆（避免你之前 crash）
        try:
            return float(change)
        except:
            return 0.0

    # =========================
    # 成交量生成
    # =========================
    def _generate_volume(self):

        base = random.randint(100, 1000)

        spike = 1.0

        # 模式影響量能
        if self.mode == "軋空行情":
            spike = random.uniform(1.5, 3.0)

        elif self.mode == "出貨":
            spike = random.uniform(1.2, 2.5)

        elif self.mode == "吸籌":
            spike = random.uniform(0.8, 1.5)

        return int(base * spike)

    # =========================
    # 五檔生成（簡化券商風格）
    # =========================
    def _generate_orderbook(self, price):

        bids = []
        asks = []

        for i in range(5):

            bid_price = round(price - (i * 0.1 + random.uniform(0, 0.05)), 2)
            ask_price = round(price + (i * 0.1 + random.uniform(0, 0.05)), 2)

            bids.append({
                "price": bid_price,
                "size": random.randint(50, 2000)
            })

            asks.append({
                "price": ask_price,
                "size": random.randint(50, 2000)
            })

        return bids, asks

    # =========================
    # 主生成函數（Streamlit用）
    # =========================
    def generate(self, tick, duration):

        self.step = tick

        change = self._generate_change()

        # 💥 安全加總（你之前 crash 就在這）
        try:
            price = float(self.last_price) + float(change)
        except:
            price = float(self.last_price)

        # 防止極端值
        price = max(price, self.base_price * 0.5)
        price = min(price, self.base_price * 1.5)

        self.last_price = price

        volume = self._generate_volume()

        bids, asks = self._generate_orderbook(price)

        # 模擬 VWAP
        vwap = price * random.uniform(0.998, 1.002)

        return {
            "name": "Simulation",
            "price": round(price, 2),
            "vwap": round(vwap, 2),
            "last_size": volume,
            "bids": bids,
            "asks": asks,
            "trade": {
                "serial": tick
            },
            "is_close": False
        }
