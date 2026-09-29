import net

def analyze(symbol):
    """Fetches futures funding and sentiment, safely falling back if geo-restricted."""
    try:
        clean_sym = symbol.replace("/", "").replace("-", "")
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        data = net.get(url, params={"symbol": clean_sym})
        
        if not data or not isinstance(data, dict) or "lastFundingRate" not in data:
            return {"deriv_regime": "no_futures", "deriv_funding": 0.0, "oi_change_24h": 0.0}
        
        funding = float(data.get("lastFundingRate", 0))
        regime = "neutral"
        if funding > 0.0005:
            regime = "longs_building"
        elif funding < -0.0005:
            regime = "short_squeeze_setup"
            
        return {
            "deriv_regime": regime,
            "deriv_funding": funding,
            "oi_change_24h": 0.0
        }
    except Exception:
        # Fallback if US server IP is blocked (Error 451)
        return {
            "deriv_regime": "geo_restricted",
            "deriv_funding": 0.0,
            "oi_change_24h": 0.0
        }