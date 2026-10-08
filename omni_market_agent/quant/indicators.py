"""
omni_market_agent/quant/indicators.py — Quantitative Technical Indicators & Divergence Signal Engine.

Grounded in Google Finance (`https://www.google.com/finance/quote/{TICKER}:{EXCHANGE}`).
Computes:
  - Simple & Exponential Moving Averages: 9, 20, 50, 200 (SMA_9, EMA_9, SMA_20, EMA_20, SMA_50, SMA_200)
  - 14-period Wilder's Relative Strength Index (RSI_14)
  - Momentum: 10-day Rate of Change (ROC) and MACD (12, 26, 9)
  - Regular & Hidden Bullish/Bearish Price-RSI Divergence + Momentum Convergence Detection
  - Daily Price Changes ($ and %) grounded in Google Finance
  - Composite Buy/Sell Signal Score (0-100) + UI Flashing Alert Triggers
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..data.google_finance import GLOBAL_GOOGLE_FINANCE, get_google_finance_url
from ..data.market_feed import GLOBAL_MARKET_FEED
from ..data.universes import get_company_name, get_ticker_universes


def compute_sma_series(values: List[float], period: int) -> List[Optional[float]]:
    """Compute Simple Moving Average (SMA) series for a given period."""
    out: List[Optional[float]] = []
    running_sum = 0.0
    for idx, val in enumerate(values):
        running_sum += val
        if idx >= period:
            running_sum -= values[idx - period]
        if idx >= period - 1:
            out.append(round(running_sum / period, 2))
        else:
            out.append(None)
    return out


def compute_ema_series(values: List[float], period: int) -> List[Optional[float]]:
    """Compute Exponential Moving Average (EMA) series for a given period."""
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    out: List[Optional[float]] = []
    ema_val: Optional[float] = None
    for idx, val in enumerate(values):
        if idx < period - 1:
            out.append(None)
        elif idx == period - 1:
            ema_val = sum(values[:period]) / period
            out.append(round(ema_val, 2))
        else:
            assert ema_val is not None
            ema_val = (val * k) + (ema_val * (1.0 - k))
            out.append(round(ema_val, 2))
    return out


def compute_rsi_series(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Compute Wilder's Relative Strength Index (RSI) series."""
    if len(closes) <= period:
        return [50.0 for _ in closes]

    rsi_out: List[Optional[float]] = [None] * period
    gains: List[float] = []
    losses: List[float] = []

    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        rsi_out.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi_out.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(0.0, delta)
        loss = max(0.0, -delta)
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        if avg_loss == 0:
            rsi_out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_out.append(round(100.0 - (100.0 / (1.0 + rs)), 2))

    return rsi_out


def compute_macd_series(
    closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Compute MACD line, Signal line, and Histogram series."""
    ema_fast = compute_ema_series(closes, fast)
    ema_slow = compute_ema_series(closes, slow)
    macd_line: List[Optional[float]] = []
    valid_macd: List[float] = []

    for f, s in zip(ema_fast, ema_slow):
        if f is None or s is None:
            macd_line.append(None)
        else:
            val = round(f - s, 3)
            macd_line.append(val)
            valid_macd.append(val)

    sig_valid = compute_ema_series(valid_macd, signal)
    signal_line: List[Optional[float]] = []
    histogram: List[Optional[float]] = []

    v_idx = 0
    for m in macd_line:
        if m is None:
            signal_line.append(None)
            histogram.append(None)
        else:
            sig_val = sig_valid[v_idx]
            v_idx += 1
            signal_line.append(sig_val)
            if sig_val is None:
                histogram.append(None)
            else:
                histogram.append(round(m - sig_val, 3))

    return macd_line, signal_line, histogram


def detect_price_rsi_divergence(
    closes: List[float], rsi_series: List[Optional[float]], window: int = 36
) -> Tuple[str, str]:
    """
    Detect Regular & Hidden Bullish/Bearish Divergence between Price pivots and Wilder's RSI(14)
    over `window` trading bars, plus 14-bar Price ROC vs. RSI delta slope comparison.
    """
    if len(closes) < window or len(rsi_series) < window:
        return "NEUTRAL_ALIGNMENT", "Insufficient bars for swing divergence detection."

    sub_closes = closes[-window:]
    sub_rsi = [float(r) if r is not None else 50.0 for r in rsi_series[-window:]]

    mid = window // 2
    first_closes, second_closes = sub_closes[:mid], sub_closes[mid:]
    first_rsi, second_rsi = sub_rsi[:mid], sub_rsi[mid:]

    low1_idx = min(range(len(first_closes)), key=lambda i: first_closes[i])
    low2_idx = min(range(len(second_closes)), key=lambda i: second_closes[i])
    p_low1, r_low1 = first_closes[low1_idx], first_rsi[low1_idx]
    p_low2, r_low2 = second_closes[low2_idx], second_rsi[low2_idx]

    high1_idx = max(range(len(first_closes)), key=lambda i: first_closes[i])
    high2_idx = max(range(len(second_closes)), key=lambda i: second_closes[i])
    p_high1, r_high1 = first_closes[high1_idx], first_rsi[high1_idx]
    p_high2, r_high2 = second_closes[high2_idx], second_rsi[high2_idx]

    # 14-bar directional slope comparison (Price % change vs. RSI point change)
    price_14d_pct = ((sub_closes[-1] - sub_closes[-15]) / sub_closes[-15]) * 100.0 if sub_closes[-15] else 0.0
    rsi_14d_delta = sub_rsi[-1] - sub_rsi[-15]

    # 1. Regular Bullish Divergence: Lower/Equal Price Low + Higher RSI Low (or 14d Price drop with rising RSI)
    if (p_low2 <= p_low1 * 1.008 and r_low2 >= r_low1 + 1.8 and r_low2 < 56.0) or (
        price_14d_pct <= -1.2 and rsi_14d_delta >= 2.0
    ):
        return (
            "BULLISH_DIVERGENCE",
            f"Bullish Price-RSI Divergence: Price swing low tested ${p_low2:.2f} (vs ${p_low1:.2f}) while RSI(14) formed a higher low ({r_low2:.1f} vs {r_low1:.1f}; 14d Price {price_14d_pct:+.1f}% vs RSI {rsi_14d_delta:+.1f} pts).",
        )

    # 2. Regular Bearish Divergence: Higher/Equal Price High + Lower RSI High (or 14d Price rise with falling RSI)
    if (p_high2 >= p_high1 * 0.992 and r_high2 <= r_high1 - 1.8 and r_high1 > 54.0) or (
        price_14d_pct >= 1.2 and rsi_14d_delta <= -2.0
    ):
        return (
            "BEARISH_DIVERGENCE",
            f"Bearish Price-RSI Divergence: Price swing high reached ${p_high2:.2f} (vs ${p_high1:.2f}) while RSI(14) formed a lower high ({r_high2:.1f} vs {r_high1:.1f}; 14d Price {price_14d_pct:+.1f}% vs RSI {rsi_14d_delta:+.1f} pts).",
        )

    # 3. Hidden Bullish Divergence: Higher Price Low + Lower RSI Low (Bullish Trend Continuation)
    if p_low2 >= p_low1 * 1.012 and r_low2 <= r_low1 - 2.0 and sub_closes[-1] >= p_low2:
        return (
            "HIDDEN_BULLISH_DIVERGENCE",
            f"Hidden Bullish Divergence: Price held a higher low (${p_low2:.2f} vs ${p_low1:.2f}) while RSI(14) reset lower ({r_low2:.1f} vs {r_low1:.1f}), signaling trend continuation.",
        )

    # 4. Hidden Bearish Divergence: Lower Price High + Higher RSI High (Bearish Trend Continuation)
    if p_high2 <= p_high1 * 0.988 and r_high2 >= r_high1 + 2.0 and sub_closes[-1] <= p_high2:
        return (
            "HIDDEN_BEARISH_DIVERGENCE",
            f"Hidden Bearish Divergence: Price formed a lower high (${p_high2:.2f} vs ${p_high1:.2f}) while RSI(14) pushed higher ({r_high2:.1f} vs {r_high1:.1f}), signaling overhead supply.",
        )

    # 5. Quantitative Momentum Convergence (Price & RSI aligned)
    if price_14d_pct >= 0.0:
        return (
            "BULLISH_CONVERGENCE",
            f"Bullish Momentum Convergence: 14d Price ({price_14d_pct:+.2f}%) and RSI(14) ({rsi_14d_delta:+.1f} pts to {sub_rsi[-1]:.1f}) are rising in alignment.",
        )
    return (
        "BEARISH_CONVERGENCE",
        f"Bearish Momentum Convergence: 14d Price ({price_14d_pct:+.2f}%) and RSI(14) ({rsi_14d_delta:+.1f} pts to {sub_rsi[-1]:.1f}) are cooling in alignment.",
    )


def analyze_ticker_technicals(
    ticker: str,
    lookback_days: int = 250,
    include_series: bool = False,
    prefer_live_google_finance: bool = False,
) -> Dict[str, Any]:
    """
    Full quantitative technical analysis for `ticker` grounded in Google Finance:
      - Price, Daily $ and % Change, Google Finance citation URL & symbol
      - Moving Averages: 9, 20, 50, 200 (SMA & EMA)
      - RSI (14) & RSI Regime
      - Momentum: 10d ROC % and MACD (12, 26, 9)
      - Regular & Hidden Bullish/Bearish Divergence detection
      - Buy/Sell Confluence Signal & UI Flash Alert triggers
    """
    symbol = ticker.strip().upper().replace(".", "-")
    gf_sym, gf_url = get_google_finance_url(symbol)
    bars = GLOBAL_MARKET_FEED.get_ohlcv_bars(
        symbol,
        lookback_days=max(220, lookback_days),
        prefer_live_google_finance=prefer_live_google_finance,
    )
    closes = [b["close"] for b in bars]

    sma_9_s = compute_sma_series(closes, 9)
    ema_9_s = compute_ema_series(closes, 9)
    sma_20_s = compute_sma_series(closes, 20)
    ema_20_s = compute_ema_series(closes, 20)
    sma_50_s = compute_sma_series(closes, 50)
    sma_200_s = compute_sma_series(closes, 200)
    rsi_14_s = compute_rsi_series(closes, 14)
    macd_l, macd_sig, macd_hist = compute_macd_series(closes, 12, 26, 9)

    price = round(float(closes[-1]), 2)
    prev_close = round(float(closes[-2]), 2) if len(closes) >= 2 else price
    daily_change_usd = round(price - prev_close, 2)
    daily_change_pct = round(((price - prev_close) / prev_close) * 100.0, 2) if prev_close else 0.0

    # Ground exact price, daily change, exchange symbol, and company name in Google Finance cache
    gf_cached = GLOBAL_GOOGLE_FINANCE.get_cached_quote(symbol)
    company_name = get_company_name(symbol)
    data_source = "Google Finance (Grounded)"
    if gf_cached:
        company_name = gf_cached.get("company_name") or company_name
        gf_url = gf_cached.get("google_finance_url") or gf_url
        gf_sym = gf_cached.get("google_finance_symbol") or gf_sym
        data_source = gf_cached.get("data_source", "Google Finance (Live)")
        if "price" in gf_cached:
            price = round(float(gf_cached["price"]), 2)
        if "daily_change_usd" in gf_cached:
            daily_change_usd = round(float(gf_cached["daily_change_usd"]), 2)
        if "daily_change_pct" in gf_cached:
            daily_change_pct = round(float(gf_cached["daily_change_pct"]), 2)

    sma_9 = sma_9_s[-1] or price
    ema_9 = ema_9_s[-1] or price
    sma_20 = sma_20_s[-1] or price
    ema_20 = ema_20_s[-1] or price
    sma_50 = sma_50_s[-1] or price
    sma_200 = sma_200_s[-1] or price
    rsi_14 = rsi_14_s[-1] if rsi_14_s[-1] is not None else 50.0

    roc_10 = round(((price - closes[-11]) / closes[-11]) * 100.0, 2) if len(closes) >= 11 else 0.0
    m_line = macd_l[-1] or 0.0
    m_sig = macd_sig[-1] or 0.0
    m_hist = macd_hist[-1] or 0.0

    div_status, div_explanation = detect_price_rsi_divergence(closes, rsi_14_s)

    if price > sma_9 > sma_20 > sma_50 > sma_200:
        ma_alignment = "BULLISH_STACK (Price > 9 > 20 > 50 > 200)"
    elif sma_50 > sma_200 and price > sma_50:
        ma_alignment = "GOLDEN_UPTREND (Price > 50 SMA > 200 SMA)"
    elif price > sma_200 and price < sma_50:
        ma_alignment = "PULLBACK_IN_UPTREND (Above 200 SMA, Below 50 SMA)"
    elif price < sma_9 < sma_20 < sma_50 < sma_200:
        ma_alignment = "BEARISH_STACK (Price < 9 < 20 < 50 < 200)"
    else:
        ma_alignment = "CONSOLIDATION_MIXED"

    if rsi_14 < 30.0:
        rsi_regime = "OVERSOLD (<30)"
    elif rsi_14 > 70.0:
        rsi_regime = "OVERBOUGHT (>70)"
    elif rsi_14 >= 53.0:
        rsi_regime = "BULLISH_MOMENTUM (53-70)"
    else:
        rsi_regime = "NEUTRAL (30-53)"

    score = 50
    reasons: List[str] = []

    if price > sma_200:
        score += 10
        reasons.append(f"Trading above 200-day SMA (${sma_200:.2f})")
    else:
        score -= 10
        reasons.append(f"Trading below 200-day SMA (${sma_200:.2f})")

    if sma_50 > sma_200:
        score += 8
        reasons.append("Golden Cross structure active (50 SMA > 200 SMA)")
    else:
        score -= 6

    if ema_9 > ema_20 and price > ema_9:
        score += 10
        reasons.append(f"Short-term momentum breakout (Price > 9 EMA ${ema_9:.2f} > 20 EMA ${ema_20:.2f})")
    elif ema_9 < ema_20:
        score -= 8

    if m_hist > 0 and roc_10 > 0:
        score += 8
        reasons.append(f"Positive MACD histogram ({m_hist:+.3f}) & 10d Momentum ({roc_10:+.2f}%)")
    elif m_hist < 0 and roc_10 < -2.0:
        score -= 8

    if rsi_14 < 32.0:
        score += 12
        reasons.append(f"Oversold RSI(14) at {rsi_14:.1f} offering mean-reversion entry")
    elif 52.0 <= rsi_14 <= 68.0:
        score += 6
        reasons.append(f"Constructive bullish RSI(14) regime ({rsi_14:.1f})")
    elif rsi_14 > 76.0:
        score -= 12
        reasons.append(f"Extended overbought RSI(14) at {rsi_14:.1f}")

    if div_status == "BULLISH_DIVERGENCE":
        score += 15
        reasons.append("Regular Bullish Price-RSI Divergence confirmed")
    elif div_status == "HIDDEN_BULLISH_DIVERGENCE":
        score += 9
        reasons.append("Hidden Bullish Price-RSI Divergence (trend continuation)")
    elif div_status == "BEARISH_DIVERGENCE":
        score -= 15
        reasons.append("Regular Bearish Price-RSI Divergence warning")
    elif div_status == "HIDDEN_BEARISH_DIVERGENCE":
        score -= 9
        reasons.append("Hidden Bearish Price-RSI Divergence warning")

    score = max(0, min(100, score))

    if score >= 75:
        action_signal = "STRONG BUY"
    elif score >= 62:
        action_signal = "BUY"
    elif score <= 28:
        action_signal = "STRONG SELL"
    elif score <= 40:
        action_signal = "SELL"
    else:
        action_signal = "HOLD"

    flash_alert = False
    flash_type = "NONE"
    if div_status in ("BULLISH_DIVERGENCE", "HIDDEN_BULLISH_DIVERGENCE"):
        flash_alert = True
        flash_type = "FLASH_BULLISH_DIVERGENCE"
    elif div_status in ("BEARISH_DIVERGENCE", "HIDDEN_BEARISH_DIVERGENCE"):
        flash_alert = True
        flash_type = "FLASH_BEARISH_DIVERGENCE"
    elif action_signal == "STRONG BUY":
        flash_alert = True
        flash_type = "FLASH_STRONG_BUY"
    elif action_signal in ("SELL", "STRONG SELL"):
        flash_alert = True
        flash_type = "FLASH_SELL_WARNING"
    elif abs(daily_change_pct) >= 2.2:
        flash_alert = True
        flash_type = "FLASH_MOMENTUM_MOVE"

    payload: Dict[str, Any] = {
        "status": "SUCCESS",
        "ticker": symbol,
        "company_name": company_name,
        "google_finance_symbol": gf_sym,
        "google_finance_url": gf_url,
        "data_source": data_source,
        "indices_membership": get_ticker_universes(symbol),
        "price": price,
        "daily_change_usd": daily_change_usd,
        "daily_change_pct": daily_change_pct,
        "volume": bars[-1]["volume"],
        "sma_9": sma_9,
        "ema_9": ema_9,
        "sma_20": sma_20,
        "ema_20": ema_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "ma_alignment": ma_alignment,
        "rsi_14": rsi_14,
        "rsi_regime": rsi_regime,
        "momentum_roc_10d_pct": roc_10,
        "macd_line": m_line,
        "macd_signal": m_sig,
        "macd_histogram": m_hist,
        "divergence_status": div_status,
        "divergence_explanation": div_explanation,
        "action_signal": action_signal,
        "signal_score": score,
        "signal_reasons": reasons[:4],
        "flash_alert": flash_alert,
        "flash_type": flash_type,
    }

    if include_series:
        # Ensure strictly ascending unique YYYY-MM-DD timestamps for TradingView Lightweight Charts
        chart_bars = []
        seen_dates = set()
        slice_len = min(150, len(bars))
        start_offset = len(bars) - slice_len
        for idx in range(slice_len):
            offset = start_offset + idx
            b = bars[offset]
            dt = b["time"]
            if dt in seen_dates:
                continue
            seen_dates.add(dt)
            chart_bars.append(
                {
                    "time": dt,
                    "open": b["open"],
                    "high": b["high"],
                    "low": b["low"],
                    "close": b["close"],
                    "volume": b["volume"],
                    "sma_9": sma_9_s[offset],
                    "sma_20": sma_20_s[offset],
                    "sma_50": sma_50_s[offset],
                    "sma_200": sma_200_s[offset],
                    "rsi_14": rsi_14_s[offset],
                    "macd_hist": macd_hist[offset],
                }
            )
        chart_bars.sort(key=lambda x: x["time"])
        payload["chart_series"] = chart_bars

    return payload
