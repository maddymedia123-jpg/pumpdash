"""Deterministic composite used to rank a watchlist and pick the shortlist sent to the agents.
Weights are unvalidated guesses - the Tracker tab tells you whether the score means anything."""
import data

MIN_LIQ = 50_000


def score(pk, follower=False):
    if pk.get("dex_liq_usd", 1e12) < MIN_LIQ:
        return 0.0
    s = 40 * pk["htf_score"]
    s += {"short_squeeze_setup": 20, "longs_building": 10}.get(pk.get("deriv_regime"), 0)
    if pk.get("chain_ok"):
        s += 20 * max(0.0, pk["chain_imbalance"]) + 5 * (pk["chain_smart_wallet_buys"] > 0)
    s += 10 * bool(follower)
    s -= 30 * bool(pk["htf_late"]) + 20 * bool(pk.get("deriv_crowded_long")) + 25 * (pk.get("chain_wash_share", 0) > 0.4)
    return round(max(0.0, min(100.0, s)), 1)


def scan(symbols, followers=()):
    rows = []
    for s in symbols:
        try:
            pk = data.build_packet(s)
            pk["scan_score"] = score(pk, s in followers)
            rows.append(pk)
        except Exception as e:  # one bad symbol must not kill the scan
            rows.append({"symbol": s, "error": str(e)[:100]})
    return rows