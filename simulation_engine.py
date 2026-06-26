import numpy as np
import random


class SimulationEngine:

    def __init__(self, mode="一般波動", base_price=100):
        self.mode = mode
        self.base_price = base_price
        self.current_price = base_price
        self.volatility = 0.01

        self.trend_bias = 0.0
        self.tick = 0

        # 🔥 主力行為參數
        self.smart_money_bias = 0.0
        self.last_price = base_price

    # =========================
    # 主生成器（核心）
    # =========================
    def generate(self, tick, duration):

        self.tick = tick

        # =========================
        # 模式控制（券商級行情）
        # =========================
        if self.mode == "軋空":
            drift = 0.002
            volatility = 0.015

        elif self.mode == "出貨":
            drift = -0.002
            volatility = 0.02

        elif self.mode == "吸籌":
            drift = 0.0005
            volatility = 0.008

        else:
            drift = 0.0002
            volatility = 0.01

        # =========================
        # 📈 趨勢隨時間變化
        # =========================
        self.trend_bias += drift + np.random.normal(0, 0.001)

        # =========================
        # 🔥 主力行為（核心修復）
        # =========================
        if random.random() < 0.03:
            self.smart_money_bias = random.choice([-0.03, 0.03])

        # 衰減
        self.smart_money_bias *= 0.9

        # =========================
        # 💰 價格生成（修復 crash）
        # =========================
        noise = np.random.normal(0, volatility)

        change = (
            self.trend_bias +
            self.smart_money_bias +
            noise
        )

        # 🔥 防止 V4 bug：避免 base_price + change 異常
        self.current_price = max(
            1,
            self.current_price * (1 + change)
        )

        # =========================
        # 📊 成交量（合理化）
        # =========================
        volume = int(abs(change) * 10000 + random.randint(50, 300))

        # =========================
        # 📡 五檔（模擬主力雷達來源）
        # =========================
        bids = self._generate_order_book(self.current_price, side="bid")
        asks = self._generate_order_book(self.current_price, side="ask")

        # =========================
        # 🧠 VWAP 模擬
        # =========================
        vwap = self.current_price * (1 + np.random.normal(0, 0.001))

        # =========================
        # 🔢 serial（修復換股 bug）
        # =========================
        serial = tick

        self.last_price = self.current_price

        return {
            "name": f"SIM-{self.mode}",
            "price": round(self.current_price, 2),
            "vwap": round(vwap, 2),
            "last_size": volume,

            "bids": bids,
            "asks": asks,

            "trade": {
                "serial": serial
            },

            "is_close": False
        }

    # =========================
    # 📦 五檔生成器（主力雷達基礎）
    # =========================
    def _generate_order_book(self, price, side="bid"):

        levels = []

        for i in range(5):

            if side == "bid":
                p = price - (i * 0.5)
            else:
                p = price + (i * 0.5)

            size = int(max(10, np.random.normal(500, 200)))

            levels.append({
                "price": round(p, 2),
                "size": size
            })

        return levels
