"""Wallet flow from recent DEX pool trades (GeckoTerminal public API, no key).
Limits: only the latest trades (~24h max), tx_from_address is the tx sender (routers/bots distort it).
Holder concentration, exchange in/outflows and labeled smart-money wallets need a keyed provider."""
import pandas as pd

import net as net_

GT = "https://api.geckoterminal.com/api/v2"
NET = {"ethereum": "eth", "solana": "solana", "base": "base", "bsc": "bsc",
       "arbitrum": "arbitrum", "polygon": "polygon_pos", "avalanche": "avax"}  # DexScreener chainId -> GT id
SMART_WALLETS = set()  # addresses you trust (lowercase for EVM); fill from your own research


def summarize(t, whale_usd=5_000, evm=True):
    t = t.copy()
    t["usd"] = pd.to_numeric(t["volume_in_usd"], errors="coerce").fillna(0)
    t["addr"] = t["tx_from_address"].str.lower() if evm else t["tx_from_address"]
    buys, sells = t[t.kind == "buy"], t[t.kind == "sell"]
    b, s = buys.usd.sum(), sells.usd.sum()
    buy_by = buys.groupby("addr").usd.sum()
    net = buy_by.sub(sells.groupby("addr").usd.sum(), fill_value=0)
    both = set(buys.addr) & set(sells.addr)  # wallets on both sides, repeatedly = wash-like
    rt = [a for a in both if (buys.addr == a).sum() >= 2 and (sells.addr == a).sum() >= 2]
    ts = pd.to_datetime(t["block_timestamp"])
    return {
        "chain_trades": len(t),
        "chain_window_min": round((ts.max() - ts.min()).total_seconds() / 60, 1),
        "chain_buy_usd": round(b), "chain_sell_usd": round(s),
        "chain_imbalance": round((b - s) / (b + s + 1e-9), 3),
        "chain_unique_buyers": int(buys.addr.nunique()), "chain_unique_sellers": int(sells.addr.nunique()),
        "chain_top5_buyer_share": round(buy_by.nlargest(5).sum() / (b + 1e-9), 3),
        "chain_whale_buys": int((buys.usd >= whale_usd).sum()),
        "chain_net_accumulators": int((net >= 1_000).sum()),
        "chain_wash_share": round(t[t.addr.isin(rt)].usd.sum() / (t.usd.sum() + 1e-9), 3),
        "chain_smart_wallet_buys": len(set(buys.addr) & SMART_WALLETS),
    }


def flow(chain, pair):
    nid = NET.get(chain or "")
    if not nid or not pair:
        return {"chain_ok": False}
    try:
        rows = net_.get_json(f"{GT}/networks/{nid}/pools/{pair}/trades")["data"]
        out = summarize(pd.DataFrame([r["attributes"] for r in rows]), evm=nid != "solana")
        return {"chain_ok": True, **out}
    except Exception:
        return {"chain_ok": False}