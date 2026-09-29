"""Higher-timeframe market structure + pattern checks (1d / 4h).
Pass CLOSED candles only, oldest -> newest, columns: open high low close volume."""


def _pivots(df, n):
    w = 2 * n + 1  # centered window: last n bars are never "confirmed" -> no lookahead
    ph = df.high[df.high == df.high.rolling(w, center=True).max()]
    pl = df.low[df.low == df.low.rolling(w, center=True).min()]
    return ph, pl


def analyze(df, n=3, base_bars=30, ext_limit=0.25):
    c, v = df.close, df.volume
    ph, pl = _pivots(df, n)
    hh = len(ph) > 1 and ph.iloc[-1] > ph.iloc[-2]
    hl = len(pl) > 1 and pl.iloc[-1] > pl.iloc[-2]
    if hh and hl:
        trend = "up"
    elif len(ph) > 1 and len(pl) > 1 and not hh and not hl:
        trend = "down"
    else:
        trend = "mixed"
    bos = bool(len(ph) and c.iloc[-1] > ph.iloc[-1])  # close above last swing high

    base = df.iloc[-base_bars - 1:-1]  # range that preceded the latest closed bar
    hi, lo = base.high.max(), base.low.min()
    bw = c.rolling(20).std() * 4 / c.rolling(20).mean()
    squeeze = bool(bw.iloc[-1] <= bw.iloc[-120:].quantile(0.2))  # bottom-20% band width
    vol_ratio = float(v.iloc[-1] / (v.iloc[-21:-1].median() + 1e-9))
    breakout = bool(c.iloc[-1] > hi and vol_ratio >= 1.5)
    touches = int((base.high >= hi * 0.99).sum())
    tri = bool(len(pl) > 2 and pl.iloc[-1] > pl.iloc[-2] > pl.iloc[-3]
               and touches >= 2 and not breakout)  # higher lows into flat resistance
    spring = bool(((df.low.iloc[-5:] < lo) & (c.iloc[-5:] > lo)).any())  # sweep below range, close back in
    ext = float(c.iloc[-1] / c.rolling(20).mean().iloc[-1] - 1)  # extension over 20-bar mean (bear flag)
    atr_pct = float(((df.high - df.low).rolling(14).mean() / c).iloc[-1])

    score = min(1.0, 0.2 * (trend == "up") + 0.2 * bos + 0.15 * squeeze + 0.25 * breakout
                + 0.15 * tri + 0.1 * spring + 0.15 * (vol_ratio >= 1.5))
    return dict(trend=trend, bos=bos, range_hi=float(hi), range_lo=float(lo), squeeze=squeeze,
                vol_ratio=round(vol_ratio, 2), breakout=breakout, asc_triangle=tri, spring=spring,
                ext=round(ext, 3), late=ext > ext_limit, atr_pct=round(atr_pct, 4), score=round(score, 2))


def report(dfs):
    """dfs: {"1d": df, "4h": df} -> flat dict, keys like '1d_trend', plus htf_score/htf_late/htf_aligned."""
    out, scores = {}, {}
    w = {"1d": 0.6, "4h": 0.4}
    for tf, df in dfs.items():
        a = analyze(df)
        scores[tf] = a["score"]
        out.update({f"{tf}_{k}": v for k, v in a.items()})
    out["htf_late"] = any(out[f"{tf}_late"] for tf in dfs)
    out["htf_aligned"] = all(out[f"{tf}_trend"] == "up" or out[f"{tf}_breakout"] for tf in dfs)
    tot = sum(w.get(tf, 0.5) for tf in dfs)
    raw = sum(w.get(tf, 0.5) * scores[tf] for tf in dfs) / tot
    out["htf_score"] = round(max(0.0, raw - (0.3 if out["htf_late"] else 0.0)), 2)
    return out