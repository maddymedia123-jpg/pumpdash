"""Money-rotation engine + analog TP/SL. Deterministic code, no LLM."""
import numpy as np
import pandas as pd


def find_followers(u, leader_chg=0.30, leader_relvol=3.0):
    """u columns: symbol, category, chg_24h (fraction), vol_24h, rel_vol (24h vol / 7d median).
    Leader = big gainer on a volume spike. Follower = same category, hasn't moved yet, volume waking up.
    'lower_vol_than_leader' is a flag, not a filter: TEST that hypothesis before trusting it."""
    out = []
    for _, L in u[(u.chg_24h >= leader_chg) & (u.rel_vol >= leader_relvol)].iterrows():
        f = u[(u.category == L.category) & (u.symbol != L.symbol)
              & (u.chg_24h < L.chg_24h * 0.5) & (u.rel_vol >= 1.5)].copy()
        f["leader"], f["leader_chg"] = L.symbol, L.chg_24h
        f["lower_vol_than_leader"] = f.vol_24h < L.vol_24h
        out.append(f)
    return pd.concat(out).sort_values("rel_vol", ascending=False) if out else pd.DataFrame()


def tp_sl(analogs, leader_gain, atr_pct, min_n=8):
    """analogs: past follower events [{event_id, peak_gain, mae, leader_chg}] as fractions, aligned by
    event time (hours after the leader's breakout), NOT calendar date. Levels are % from entry."""
    if len(analogs) >= min_n and len({a.get("event_id") for a in analogs}) >= 5:
        r = np.array([a["peak_gain"] / a["leader_chg"] for a in analogs])
        tps = list(np.percentile(r, [25, 50, 75]) * leader_gain)
        sl = float(np.percentile([a["mae"] for a in analogs], 75))
        src, evidence = f"{len(analogs)} analogs", True
    else:  # placeholders only - there is no evidence behind these targets
        sl = 1.5 * atr_pct
        tps = [2 * sl, 3 * sl, 5 * sl]
        src, evidence = "ATR placeholder (too few analogs)", False
    rr = tps[1] / sl
    return {"TP1": float(tps[0]), "TP2": float(tps[1]), "TP3": float(tps[2]), "SL": float(sl), "RR": float(rr),
            "source": src, "tradeable": bool(evidence and rr >= 2)}