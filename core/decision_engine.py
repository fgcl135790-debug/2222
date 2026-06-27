def make_decision(
    price,
    ema5,
    ema20,
    ema60,
    rsi,
    macd,
    macd_signal,
    bid_ratio,
    rebound,
):

    score = 0
    reasons = []

    # =========================
    # EMA
    # =========================
    if ema5 > ema20:
        score += 20
        reasons.append("EMA5站上EMA20")

    if ema20 > ema60:
        score += 15
        reasons.append("EMA20站上EMA60")

    # =========================
    # MACD
    # =========================
    if macd > macd_signal:
        score += 15
        reasons.append("MACD黃金交叉")

    # =========================
    # RSI
    # =========================
    if 40 <= rsi <= 70:
        score += 15
        reasons.append("RSI健康")

    elif rsi < 30:
        score += 10
        reasons.append("RSI超賣")

    # =========================
    # 主力
    # =========================
    if bid_ratio > 1.3:
        score += 20
        reasons.append("主力偏多")

    elif bid_ratio < 0.8:
        score -= 20
        reasons.append("主力偏空")

    # =========================
    # 反彈
    # =========================
    score += rebound * 0.2

    # =========================
    # 決策
    # =========================
    if score >= 75:

        action = "BUY"

    elif score <= 35:

        action = "SELL"

    else:

        action = "WAIT"

    # =========================
    # 停損停利
    # =========================
    stop_loss = round(price * 0.992, 2)
    take_profit = round(price * 1.015, 2)

    rr = round(
        (take_profit - price) /
        (price - stop_loss),
        2
    )

    return {

        "action": action,

        "score": round(score),

        "entry": price,

        "stop_loss": stop_loss,

        "take_profit": take_profit,

        "rr": rr,

        "reasons": reasons

    }
