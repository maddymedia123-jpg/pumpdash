import json
import os
import pandas as pd
import time

def evaluate(path="signals.jsonl"):
    if not os.path.exists(path):
        return pd.DataFrame()
    
    records = []
    try:
        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception:
        return pd.DataFrame()

    if not records:
        return pd.DataFrame()

    rows = []
    for r in records:
        pk = r.get("packet", {})
        v = r.get("verdict", {})
        rows.append({
            "time": time.strftime('%Y-%m-%d %H:%M', time.localtime(r.get("t", time.time()))),
            "symbol": pk.get("symbol", "N/A"),
            "score": pk.get("scan_score", 50),
            "timeframe": pk.get("timeframe", "1h"),
            "verdict": v.get("verdict", "scanned"),
            "status": "Active / Live Tracking"
        })
    return pd.DataFrame(rows)

def summary(df):
    if df.empty:
        return pd.DataFrame()
    return pd.DataFrame([{
        "Total Signals Logged": len(df),
        "Unique Symbols": df["symbol"].nunique(),
        "Top Signal": df.sort_values(by="score", ascending=False).iloc[0]["symbol"] if "score" in df else "N/A"
    }])