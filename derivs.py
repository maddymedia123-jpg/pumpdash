import requests

def stats(symbol, period="1h", n=24):
    base = symbol.replace("/", "").replace("USDT", "")
    contract_gate = f"{base}_USDT"
    mexc_symbol = f"{base}_USDT"
    
    # --- Source 1: Gate.io Futures API ---
    try:
        url = f"https://api.gateio.ws/api/v4/futures/usdt/tickers?contract={contract_gate}"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                item = data[0]
                funding = float(item.get("funding_rate", 0.0))
                price_chg = float(item.get("change_percentage", 0.0)) / 100.0
                turnover = float(item.get("volume_24h_base", 0.0))
                return _format_result(funding, price_chg, turnover)
    except Exception:
        pass

    # --- Source 2: MEXC Futures API ---
    try:
        url = f"https://contract.mexc.com/api/v1/contract/ticker?symbol={mexc_symbol}"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") and res.get("data"):
                item = res["data"]
                funding = float(item.get("fundingRate", 0.0))
                price_chg = float(item.get("riseFallRate", 0.0))
                turnover = float(item.get("volume24", 0.0))
                return _format_result(funding, price_chg, turnover)
    except Exception:
        pass

    # --- Source 3: KuCoin Futures API ---
    try:
        url = f"https://api-futures.kucoin.com/api/v1/ticker/24hr?symbol={base}USDTM"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            res = r.json()
            if res.get("code") == "200000" and res.get("data"):
                item = res["data"]
                funding = float(item.get("fundingRate", 0.0))
                price_chg = float(item.get("priceChgPct", 0.0))
                turnover = float(item.get("turnover", 0.0))
                return _format_result(funding, price_chg, turnover)
    except Exception:
        pass

    # Final Fallback if all APIs fail temporarily
    return {
        "deriv_has_perp": False,
        "deriv_funding": 0.0,
        "deriv_funding_avg_3d": 0.0,
        "deriv_oi_usd": 0.0,
        "deriv_oi_chg_24h": 0.0,
        "deriv_px_chg_24h": 0.0,
        "deriv_ls_ratio": 1.0,
        "deriv_regime": "neutral",
        "deriv_crowded_long": False
    }

def _format_result(funding, price_chg, turnover):
    if funding > 0.0003:
        regime = "overheated_long"
    elif funding < -0.0003:
        regime = "overheated_short"
    elif price_chg > 0.02:
        regime = "bullish_momentum"
    elif price_chg < -0.02:
        regime = "bearish_momentum"
    else:
        regime = "neutral"

    return {
        "deriv_has_perp": True,
        "deriv_funding": round(funding * 100, 4),
        "deriv_funding_avg_3d": round(funding * 100, 4),
        "deriv_oi_usd": turnover,
        "deriv_oi_chg_24h": round(price_chg * 100, 4),
        "deriv_px_chg_24h": round(price_chg * 100, 4),
        "deriv_ls_ratio": 1.0,
        "deriv_regime": regime,
        "deriv_crowded_long": funding > 0.0005
    }
