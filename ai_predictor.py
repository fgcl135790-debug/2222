import numpy as np


class AIPredictor:

    # =========================
    # 主入口（券商級判斷）
    # =========================
    @staticmethod
    def predict_trade(price_history,
                      volume_history,
                      ema5,
                      ema20,
                      ema60,
                      rsi,
                      macd,
                      macd_signal,
                      momentum,
                      bid_ratio,
                      vwap):

        score = 50  # 中性起點

        reasons = []

        # =========================
        # 📊 趨勢判斷（平滑版，不敏感）
        # =========================
        if ema5 > ema20 > ema60:
            score += 18
            reasons.append("多頭排列")

        elif ema5 < ema20 < ema60:
            score -= 18
            reasons.append("空頭排列")

        # =========================
        # 💰 VWAP（主力成本）
        # =========================
        if price_history[-1] > vwap:
            score += 10
            reasons.append("站上VWAP")
        else:
            score -= 10
            reasons.append("跌破VWAP")

        # =========================
        # 🔥 RSI（非極端化）
        # =========================
        if rsi > 70:
            score -= 8
        elif rsi < 30:
            score += 8

        # =========================
        # 📉 MACD（趨勢延伸）
        # =========================
        if macd > macd_signal:
            score += 10
        else:
            score -= 10

        # =========================
        # 🚀 動能（修正過度敏感）
        # =========================
        if momentum > 0:
            score += 6
        else:
            score -= 6

        # =========================
        # 🧠 主力籌碼（重點）
        # =========================
        if bid_ratio > 1.5:
            score += 14
            reasons.append("主力買盤強")
        elif bid_ratio < 0.7:
            score -= 14
            reasons.append("主力賣壓大")

        # =========================
        # 📦 成交量趨勢（修復）
        # =========================
        if len(volume_history) > 5:
            vol_trend = np.mean(volume_history[-3:]) - np.mean(volume_history[-10:])

            if vol_trend > 0:
                score += 5
                reasons.append("量能放大")
            else:
                score -= 5
                reasons.append("量能萎縮")

        # =========================
        # 🔒 限制（避免爆分）
        # =========================
        score = max(0, min(100, int(score)))

        # =========================
        # 📈 市場語意（你要的 V5 核心）
        # =========================
        if score >= 70:
            market_state = "做多偏多"
        elif score <= 30:
            market_state = "做空偏空"
        else:
            market_state = "盤整觀望"

        # =========================
        # 🎯 反彈機率（核心新增）
        # =========================
        rebound_prob = 0

        if rsi < 35 and momentum > 0:
            rebound_prob = 70
        elif rsi < 45:
            rebound_prob = 55
        else:
            rebound_prob = 35

        # =========================
        # ⚠️ 風險分數（Risk Engine）
        # =========================
        risk = 0

        if rsi > 75:
            risk += 30
        if macd < macd_signal:
            risk += 20
        if bid_ratio < 0.8:
            risk += 20

        risk = min(100, risk)

        # =========================
        # 🧠 最終決策（不是提示，是策略）
        # =========================
        if score >= 65 and risk < 50:
            signal = "BUY"
        elif score <= 35 and risk < 60:
            signal = "SELL"
        else:
            signal = "HOLD"

        # =========================
        # 📤 回傳（V5.5 完整結構）
        # =========================
        return {
            "score": score,
            "reasons": reasons,
            "market_state": market_state,
            "signal": signal,
            "rebound_prob": rebound_prob,
            "risk": risk
        }
