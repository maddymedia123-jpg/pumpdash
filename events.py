"""Builds the rotation event history that TP/SL analogs and the edge test depend on.
Event time t = first hour a leader pumps (24h gain >= lead_chg on >= lead_rv volume). Followers are judged with the
SAME rule the live scanner uses (haven't moved, volume waking up), entry = follower close at t, outcomes over next H hours."""
import numpy as np
import pandas as pd

import data

H = 72  # forward window, hourly bars


def _feat(df):
    d = df.set_index("ts").copy()
    d["v24"] = (d.volume * d.close).rolling(24).sum()
    d["chg24"] = d.close / d.close.shift(24) - 1
    d["relvol"] = d.v24 / d.v24.rolling(24 * 7).median().shift(1)  # baseline excludes current bar
    d["fwd_peak"] = d.high[::-1].rolling(H, min_periods=H).max()[::-1].shift(-1) / d.close - 1
    return d


def build(cats_csv, days=120, lead_chg=0.30, lead_rv=3.0, cool_h=72, hit=0.15):
    cats = pd.read_csv(cats_csv)
    F = {}
    for r in cats.itertuples():
        try:
            F[r.symbol] = (r.category, _feat(data.history(r.symbol, "1h", days)))
        except Exception:
            continue  # delisted / no history: skip
    base = {s: float((d.fwd_peak.dropna() >= hit).mean()) for s, (_, d) in F.items()}  # unconditional hit rate
    ev, eid = [], 0
    for L, (cat, dl) in F.items():
        last = -10 ** 15
        for t in dl[(dl.chg24 >= lead_chg) & (dl.relvol >= lead_rv)].index:
            if t - last < cool_h * 3_600_000:
                continue
            last, eid = t, eid + 1
            lr = dl.loc[t]
            for S, (cs, ds) in F.items():
                if S == L or cs != cat or t not in ds.index:
                    continue
                r = ds.loc[t]
                if not (r.chg24 < 0.5 * lr.chg24 and r.relvol >= 1.5) or np.isnan(r.fwd_peak):
                    continue
                w = ds.loc[t:].iloc[1:H + 1]
                k = int(np.argmax(w.high.values))
                ev.append(dict(event_id=eid, t=t, leader=L, follower=S, category=cat, leader_chg=lr.chg24,
                               follower_chg=r.chg24, follower_relvol=r.relvol, lower_vol_than_leader=bool(r.v24 < lr.v24),
                               peak_gain=r.fwd_peak, mae=max(0.0, 1 - w.low.iloc[:k + 1].min() / r.close),
                               hrs_to_peak=k + 1, base_hit15=base[S]))
    return pd.DataFrame(ev)


def edge(ev, hit=0.15):
    """hit15 vs baseline = the test of whether rotation adds anything. Also tests the 'lower volume than leader' rule."""
    f = ev.assign(hit15=ev.peak_gain >= hit)
    agg = dict(n=("hit15", "size"), leader_events=("event_id", "nunique"), hit15=("hit15", "mean"),
               baseline=("base_hit15", "mean"), median_peak=("peak_gain", "median"), median_mae=("mae", "median"))
    by = f.groupby("lower_vol_than_leader").agg(**agg)
    return pd.concat([f.assign(g="all").groupby("g").agg(**agg), by.rename(index=lambda x: f"lower_vol={x}")])