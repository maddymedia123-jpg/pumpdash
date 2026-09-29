"""Binance USDT-M futures: funding, open interest, long/short ratio (public endpoints, no key).
Liquidation maps need a paid provider (e.g. CoinGlass) and are NOT wired here."""
import numpy as np
import requests

import net

F = "https://fapi.binance.com"


def _get(path, **params):
    return net.get_json(F + path, params)


def classify(oi_chg, px_chg, funding):
    if oi_chg > 0.05 and px_chg <= 0.02 and funding < 0:
        return "short_squeeze_setup"  # shorts piling in while price holds
    if oi_chg > 0.05 and px_chg > 0.02:
        return "longs_building"
    if oi_chg < -0.03 and px_chg > 0.03:
        return "short_covering"  # squeeze already underway -> likely late
    if oi_chg < -0.03 and px_chg < -0.03:
        return "deleveraging"
    return "neutral"


def stats(symbol, period="1h", n=24):
    """symbol like 'ENSO/USDT'. Returns {'deriv_has_perp': False} if no perp or the call fails."""
    s = symbol.replace("/", "")
    try:
        prem = _get("/fapi/v1/premiumIndex", symbol=s)
        oi = _get("/futures/data/openInterestHist", symbol=s, period=period, limit=n)
        ls = _get("/futures/data/globalLongShortAccountRatio", symbol=s, period=period, limit=n)
        fr = _get("/fapi/v1/fundingRate", symbol=s, limit=9)
        kl = _get("/fapi/v1/klines", symbol=s, interval=period, limit=n)
        oi_v = [float(x["sumOpenInterestValue"]) for x in oi]
        px = [float(k[4]) for k in kl]
        funding = float(prem["lastFundingRate"])
        oi_chg, px_chg = oi_v[-1] / oi_v[0] - 1, px[-1] / px[0] - 1
        return {"deriv_has_perp": True, "deriv_funding": funding,
                "deriv_funding_avg_3d": float(np.mean([float(x["fundingRate"]) for x in fr])),
                "deriv_oi_usd": oi_v[-1], "deriv_oi_chg_24h": round(oi_chg, 4),
                "deriv_px_chg_24h": round(px_chg, 4), "deriv_ls_ratio": float(ls[-1]["longShortRatio"]),
                "deriv_regime": classify(oi_chg, px_chg, funding),
                "deriv_crowded_long": funding > 0.0005}  # elevated positive funding = bear evidence
    except requests.HTTPError as e:  # Binance answers 400 for symbols with no perp
        no_perp = e.response is not None and e.response.status_code == 400
        return {"deriv_has_perp": False} if no_perp else {"deriv_ok": False}
    except Exception:
        return {"deriv_ok": False}