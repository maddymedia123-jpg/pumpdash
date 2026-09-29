import os
import ccxt
import pandas as pd
import derivs
import onchain
import htf
import json
import time

def get_active_exchanges():
    """Initializes reliable global exchanges using correct CCXT class names."""
    exchanges = []
    for ex_cls in [ccxt.bybit, ccxt.kucoin, ccxt.gate, ccxt.mexc]:
        try:
            exchanges.append(ex_cls({'enableRateLimit': True}))
        except Exception:
            pass
    return exchanges

def fetch_top_market_pairs(limit=50):
    """Dynamically fetches top volume USDT pairs across active exchanges."""
    pairs = set()
    for ex in get_active_exchanges():
        try:
            tickers = ex.fetch_tickers()
            usdt_pairs = [
                (symbol, ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) or 0)
                for symbol, ticker in tickers.items()
                if symbol.endswith('/USDT') and not any(x in symbol for x in ['UP/', 'DOWN/', 'BEAR/', 'BULL/'])
            ]
            sorted_pairs = sorted(usdt_pairs, key=lambda x: x[1], reverse=True)
            for symbol, _ in sorted_pairs[:limit]:
                pairs.add(symbol)
            if len(pairs) >= limit:
                break
        except Exception:
            continue
    return list(pairs)[:limit] if pairs else ["SOL/USDT", "BTC/USDT", "ETH/USDT", "TAO/USDT", "PEPE/USDT"]

def fetch_ohlcv_multi(symbol, timeframe="1h", limit=100):
    """Attempts to fetch candle data across multiple global exchanges."""
    for ex in get_active_exchanges():
        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if ohlcv and len(ohlcv) > 0:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                return df
        except Exception:
            continue
    return pd.DataFrame()

def build_packet(symbol, timeframe="1h", chain=None, pair=None):
    """Builds an integrated analysis packet for a given symbol."""
    df_tf = fetch_ohlcv_multi(symbol, timeframe, 100)
    df_1d = fetch_ohlcv_multi(symbol, "1d", 100) if timeframe != "1d" else df_tf
    
    htf_res = htf.analyze(df_tf, df_1d) if not df_tf.empty else {}
    der_res = derivs.analyze(symbol)
    chain_res = onchain.analyze(symbol, chain, pair) if hasattr(onchain, 'analyze') else {}
    
    packet = {
        "symbol": symbol,
        "timeframe": timeframe,
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