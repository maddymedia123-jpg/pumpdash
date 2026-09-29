import json
import time

import ccxt
import pandas as pd

import derivs
import htf
import net
import onchain

_ex = ccxt.binance({"enableRateLimit": True})
COLS = ["ts", "open", "high", "low", "close", "volume"]


def ohlcv(symbol, tf="4h", limit=300):
    df = pd.DataFrame(_ex.fetch_ohlcv(symbol, tf, limit=limit), columns=COLS)
    return df.iloc[:-1].reset_index(drop=True)  # drop the still-forming candle


def history(symbol, tf="1h", days=120):
    """Paginated candles (ts in ms), closed candles only."""
    step = _ex.parse_timeframe(tf) * 1000
    since, rows = _ex.milliseconds() - days * 86_400_000, []
    while True:
        b = _ex.fetch_ohlcv(symbol, tf, since=since, limit=1000)
        if not b:
            break
        rows += b
        since = b[-1][0] + step
        if len(b) < 1000:
            break
    df = pd.DataFrame(rows, columns=COLS).drop_duplicates("ts")
    return df.iloc[:-1].reset_index(drop=True)


def dex_stats(query):
    """Ticker search is NOT safe (clone tokens share tickers) - pass chain+pair to build_packet to override."""
    pairs = net.get_json("https://api.dexscreener.com/latest/dex/search", {"q": query}).get("pairs") or []
    if not pairs:
        return {}
    p = max(pairs, key=lambda x: (x.get("liquidity") or {}).get("usd", 0))
    return {"dex_chain": p.get("chainId"), "dex_pair": p.get("pairAddress"),
            "dex_price": float(p.get("priceUsd") or 0),
            "dex_liq_usd": (p.get("liquidity") or {}).get("usd", 0),
            "dex_vol_1h": (p.get("volume") or {}).get("h1", 0),
            "dex_vol_24h": (p.get("volume") or {}).get("h24", 0),
            "dex_chg_1h": (p.get("priceChange") or {}).get("h1", 0)}


def build_packet(symbol, chain=None, pair=None):
    pk = {"symbol": symbol}
    pk.update(htf.report({tf: ohlcv(symbol, tf) for tf in ("1d", "4h")}))  # required: errors propagate
    try:
        pk.update(dex_stats(symbol.split("/")[0]))
    except Exception:
        pk["dex_ok"] = False
    if chain and pair:
        pk.update({"dex_chain": chain, "dex_pair": pair})
    pk.update(derivs.stats(symbol))  # optional feeds degrade to *_ok/has_perp flags instead of crashing
    pk.update(onchain.flow(pk.get("dex_chain"), pk.get("dex_pair")))
    return pk


def universe(categories_csv):
    """categories_csv: symbol,category (your own narrative map)."""
    cats = pd.read_csv(categories_csv)
    tick = _ex.fetch_tickers(list(cats.symbol))
    rows = []
    for _, r in cats.iterrows():
        t = tick.get(r.symbol)
        if not t:
            continue
        d = ohlcv(r.symbol, "1d", 10)
        base = (d.volume * d.close).iloc[-8:].median()
        rows.append({"symbol": r.symbol, "category": r.category, "chg_24h": (t["percentage"] or 0) / 100,
                     "vol_24h": t["quoteVolume"] or 0, "rel_vol": (t["quoteVolume"] or 0) / (base + 1e-9)})
    return pd.DataFrame(rows)


def log_signal(packet, verdict, path="signals.jsonl"):
    with open(path, "a") as f:
        f.write(json.dumps({"t": time.time(), "packet": packet, "verdict": verdict}, default=str) + "\n")