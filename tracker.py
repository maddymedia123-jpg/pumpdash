"""Scores logged signals against what price did next. This is how you find out whether any of it works."""
import json
import os
import time

import pandas as pd

import data

H = 72  # outcome window, hourly bars


def evaluate(path="signals.jsonl", hit=0.15):
    if not os.path.exists(path):
        return pd.DataFrame()
    sigs = sorted((json.loads(l) for l in open(path)), key=lambda s: s["t"])
    seen, rows = {}, []
    for s in sigs:
        pk, key = s["packet"], (s["packet"].get("symbol"), (s.get("verdict") or {}).get("verdict"))
        if time.time() - s["t"] < H * 3600 or s["t"] - seen.get(key, 0) < 86_400:
            continue  # not matured yet, or duplicate of the same symbol+verdict within 24h
        seen[key] = s["t"]
        try:
            c = data._ex.fetch_ohlcv(pk["symbol"], "1h", since=int(s["t"] * 1000), limit=H)
        except Exception:
            continue
        if len(c) < H:
            continue
        w = pd.DataFrame(c, columns=data.COLS)
        entry, k = w.open.iloc[0], int(w.high.values.argmax())
        peak = w.high.max() / entry - 1
        rows.append(dict(t=pd.to_datetime(s["t"], unit="s"), symbol=pk["symbol"], verdict=key[1],
                         scan_score=pk.get("scan_score", 0), peak_gain=peak,
                         mae=max(0.0, 1 - w.low.iloc[:k + 1].min() / entry), hit15=peak >= hit))
    return pd.DataFrame(rows)


def summary(df):
    df = df.assign(score_bucket=pd.cut(df.scan_score, [-1, 40, 60, 80, 101]).astype(str))
    agg = dict(n=("hit15", "size"), hit15=("hit15", "mean"), median_peak=("peak_gain", "median"),
               median_mae=("mae", "median"))
    return pd.concat({"by_verdict": df.groupby("verdict").agg(**agg), "by_score": df.groupby("score_bucket").agg(**agg)})