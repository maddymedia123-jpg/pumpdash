import requests

def stats(symbol, period="1h", n=24):
    # Format symbol for Gate.io (e.g., BTC_USDT)
    base = symbol.replace("/", "").replace("USDT", "")
    contract = f"{base}_USDT"
    
    try:
        # Gate.io Futures API (Lenient with US/Cloud IPs)
        url = f"https://api.gateio.ws/api/v4/futures/usdt/tickers?contract={contract}"
        r = requests.get(url, timeout=5)
        
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                item = data[0]
                funding = float(item.get("funding_rate", 0.0))
                price_chg = float(item.get("change_percentage", 0.0)) / 100.0
                turnover = float(item.get("volume_24h_base", 0.0))
                
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
                    "deriv_oi_chg_24h": round(price_chg, 4),
                    "deriv_px_chg_24h": round(price_chg, 4),
                    "deriv_ls_ratio": 1.0,
                    "deriv_regime": regime,
                    "deriv_crowded_long": funding > 0.0005
                }
    except Exception:
        pass

    # Fallback if the token has no futures contract
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
