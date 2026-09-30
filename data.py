import os
import ccxt
import pandas as pd
import derivs
import onchain
import htf
import json
import time

DEFAULT_CATEGORIES = {
    "SOL/USDT": "L1", "BTC/USDT": "Major", "ETH/USDT": "Major", "BNB/USDT": "L1",
    "XRP/USDT": "Major", "ADA/USDT": "L1", "AVAX/USDT": "L1", "SUI/USDT": "L1",
    "NEAR/USDT": "AI", "TAO/USDT": "AI", "FET/USDT": "AI", "RENDER/USDT": "AI",
    "PEPE/USDT": "Meme", "WIF/USDT": "Meme", "DOGE/USDT": "Meme", "SHIB/USDT": "Meme",
    "FLOKI/USDT": "Meme", "BONK/USDT": "Meme", "PUMP/USDT": "Meme", "QNT/USDT": "Infra",
    "LINK/USDT": "Infra", "UNI/USDT": "DeFi", "AAVE/USDT": "DeFi"
}

def ensure_categories_file(cats_file="categories.csv"):
    if not os.path.exists(cats_file):
        df = pd.DataFrame([{"symbol": k, "category": v} for k, v in DEFAULT_CATEGORIES.items()])
        df.to_csv(cats_file, index=False)

def get_active_exchanges():
    exchanges = []
    for ex_cls in [ccxt.bybit, ccxt.kucoin, ccxt.gate, ccxt.mexc]:
        try:
            exchanges.append(ex_cls({'enableRateLimit': True}))
        except Exception:
            pass
    return exchanges

def fetch_top_market_pairs(limit=50):
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
    return list(pairs)[:limit] if pairs else list(DEFAULT_CATEGORIES.keys())

def fetch_ohlcv_multi(symbol, timeframe="1h", limit=100):
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
    df_tf = fetch_ohlcv_multi(symbol, timeframe, 100)
    df_1d = fetch_ohlcv_multi(symbol, "1d", 100) if timeframe != "1d" else df_tf
    
    htf_res = htf.analyze(df_tf, df_1d)
    
    if hasattr(derivs, 'stats'):
        der_res = derivs.stats(symbol, timeframe)
    elif hasattr(derivs, 'analyze'):
        der_res = derivs.analyze(symbol)
    else:
        der_res = {}
        
    chain_res = onchain.analyze(symbol, chain, pair) if hasattr(onchain, 'analyze') else {}
    
    chg_24h, rel_vol = 0.0, 1.0
    if not df_tf.empty and len(df_tf) >= 2:
        chg_24h = float((df_tf['close'].iloc[-1] - df_tf['close'].iloc[0]) / df_tf['close'].iloc[0])
        vol_mean = df_tf['volume'].mean()
        if vol_mean > 0:
            rel_vol = float(df_tf['volume'].iloc[-1] / vol_mean)

    cat = DEFAULT_CATEGORIES.get(symbol, "General")

    packet = {
        "symbol": symbol,
        "category": cat,
        "chg_24h": chg_24h,
        "rel_vol": rel_vol,
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
    ensure_categories_file(cats_file)
    return pd.read_csv(cats_file)
