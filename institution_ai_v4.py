import numpy as np


class InstitutionalAIV4:

    @staticmethod
    def analyze(
        price,
        prices,
        vwap,
        ema5,
        ema20,
        ema60,
        rsi,
        macd,
        macd_signal,
        total_bid,
        total_ask,
        volume,
        volumes,
        volatility,
    ):

        score = 50
        reasons = []

        # =========================
        # 1. 主力方向（Order Flow）
        # =========================
        imbalance = (total_bid - total_ask) / max(total_bid + total_ask, 1)

        if imbalance > 0.3:
            score += 20
            reasons.append("🏦 主力強力吸籌")

        elif imbalance > 0.1:
            score += 10
            reasons.append("📊 偏多吸收")

        elif imbalance < -0.3:
            score -= 20
            reasons.append("📉 主力出貨")

        elif imbalance < -0.1:
            score -= 10
            reasons.append("📊 偏空壓盤")

        # =========================
        # 2. VWAP（法人基準線）
        # =========================
        if price > vwap:
            score += 10
            reasons.append("📈 站上VWAP（多頭控制）")
        else:
            score -= 10
            reasons.append("📉 跌破VWAP（弱勢）")

        # =========================
        # 3. 均線結構（機構趨勢）
        # =========================
        if ema5 > ema20 > ema60:
            score += 20
            reasons.append("🔥 多頭排列（機構趨勢）")

        elif ema5 < ema20 < ema60:
            score -= 20
            reasons.append("❄ 空頭排列（機構壓制）")

        # =========================
        # 4. RSI（過熱/過冷）
        # =========================
        if rsi < 30:
            score += 10
            reasons.append("🧊 超賣區（反彈機會）")

        elif rsi > 70:
            score -= 10
            reasons.append("🔥 超買區（回調風險）")

        # =========================
        # 5. MACD（趨勢動能）
        # =========================
        if macd > macd_signal:
            score += 10
            reasons.append("📈 MACD多頭")

        else:
            score -= 10
            reasons.append("📉 MACD空頭")

        # =========================
        # 6. 成交量（機構進場）
        # =========================
        vol_ma = np.mean(volumes[-20:]) if len(volumes) > 20 else np.mean(volumes)

        if volume > vol_ma * 1.5:
            score += 15
            reasons.append("💥 爆量進場（機構介入）")

        elif volume < vol_ma * 0.7:
            score -= 5
            reasons.append("😴 量能萎縮")

        # =========================
        # 7. 波動率（風險）
        # =========================
        if volatility > 3:
            score += 5
            reasons.append("⚡ 高波動（機會+風險）")

        elif volatility < 0.5:
            score -= 5
            reasons.append("🧘 低波動（盤整）")

        # =========================
        # 8. 最終AI分數
        # =========================
        score = max(0, min(int(score), 100))

        # =========================
        # 9. 機構級訊號（不是BUY/SELL）
        # =========================
        if score >= 85:
            signal = "🚀 主力攻擊波段（強多）"

        elif score >= 70:
            signal = "📈 機構偏多（可進場）"

        elif score >= 55:
            signal = "⚖ 多空整理（觀望）"

        elif score >= 40:
            signal = "📉 偏弱（減碼）"

        else:
            signal = "❄ 主力撤退（風險區）"

        return signal, score, reasons
