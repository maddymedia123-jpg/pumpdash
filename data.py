import os
import ccxt
import pandas as pd
import derivs
import onchain
import htf
import json
import time

def fetch_ohlcv_multi(symbol, timeframe="1h", limit=100):
    """Attempts to fetch candle data across multiple global exchanges."""
    exchanges = [
        ccxt.bybit({'enableRateLimit': True}),
        ccxt.kucoin({'enableRateLimit': True}),
        ccxt.gateio({'enableRateLimit': True}),
        ccxt.binance({'enableRateLimit': True})
    ]
    for ex in exchanges:
        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if ohlcv and len(ohlcv) > 0:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                return df
        except Exception:
            continue
    return pd.DataFrame()

def build_packet(symbol, chain=None, pair=None):
    """Builds an integrated analysis packet for a given symbol."""
    df_4h = fetch_ohlcv_multi(symbol, "4h", 100)
    df_1d = fetch_ohlcv_multi(symbol, "1d", 100)
    
    htf_res = htf.analyze(df_4h, df_1d) if not df_4h.empty else {}
    der_res = derivs.analyze(symbol)
    chain_res = onchain.analyze(symbol, chain, pair) if hasattr(onchain, 'analyze') else {}
    
    packet = {
        "symbol": symbol,
        "timestamp": int(time.time()),
        "4h_atr_pct": htf_res.get("atr_pct", 0.05),
        "htf_score": htf_res.get("htf_score", 50),
        "htf_aligned": htf_res.get("htf_aligned", False),
        "htf_late": htf_res.get("htf_late", False),
        "deriv_regime": der_res.get("deriv_regime", "neutral"),
        "deriv_funding": der_res.get("deriv_funding", 0.0),
        "chain_imbalance": chain_res.get("imbalance", 0.0),
        "chain_wash_share": chain_res.get("wash_share", 0.0),
        "dex_liq_usd": chain_res.get("dex_liq_usd", 100000.0)
    }
    return packet

def log_signal(packet, verdict, path="signals.jsonl"):
    try:
        record = {"t": int(time.time()), "packet": packet, "verdict": verdict}
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

def universe(cats_file="categories.csv"):
    if not os.path.exists(cats_file):
        return pd.DataFrame()
    return pd.read_csv(cats_file)