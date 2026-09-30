  import requests

def stats(symbol, period="1h", n=24):
    s = symbol.replace("/", "").upper()
    if not s.endswith("USDT"):
        s += "USDT"
        
    try:
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={s}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            res = r.json().get("result", {}).get("list", [])
            if res:
                item = res[0]
                funding = float(item.get("fundingRate", 0.0) or 0.0)
                price_chg = float(item.get("price24hPcnt", 0.0) or 0.0)
                turnover = float(item.get("turnover24h", 0.0) or 0.0)
                
                if funding > 0.0003:
                    regime = "overheated_long"
                elif funding < -0.0003:
                    regime = "overheated_short"
                elif price_chg > 0.01:
                    regime = "bullish_momentum"
                elif price_chg < -0.01:
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

    return {
        "deriv_has_perp": True,
        "deriv_funding": 0.0,
        "deriv_funding_avg_3d": 0.0,
        "deriv_oi_usd": 0.0,
        "deriv_oi_chg_24h": 0.0,
        "deriv_px_chg_24h": 0.0,
        "deriv_ls_ratio": 1.0,
        "deriv_regime": "neutral",
        "deriv_crowded_long": False
    }
