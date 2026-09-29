import pandas as pd
import data

def find_followers(u=None, leader_chg=0.03, leader_relvol=1.0):
    if u is None or (isinstance(u, pd.DataFrame) and u.empty):
        u = data.universe()

    if isinstance(u, list):
        u = pd.DataFrame(u)

    records = []
    symbols = u['symbol'].tolist() if 'symbol' in u.columns else ["SOL/USDT", "TAO/USDT", "FET/USDT", "PEPE/USDT", "WIF/USDT", "NEAR/USDT"]
    
    for sym in symbols[:15]:
        pk = data.build_packet(sym)
        cat = pk.get("category", "General")
        records.append({
            "symbol": sym,
            "category": cat,
            "chg_24h": pk.get("chg_24h", 0.0),
            "rel_vol": pk.get("rel_vol", 1.0)
        })

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()

    followers = []
    leaders = df[(df["chg_24h"] >= leader_chg) & (df["rel_vol"] >= leader_relvol)]

    for _, L in leaders.iterrows():
        cat = L["category"]
        same_cat = df[(df["category"] == cat) & (df["symbol"] != L["symbol"])]
        for _, F in same_cat.iterrows():
            if F["chg_24h"] < L["chg_24h"]:
                followers.append({
                    "symbol": F["symbol"],
                    "category": cat,
                    "leader": L["symbol"],
                    "leader_chg_24h": f"{L['chg_24h'] * 100:.2f}%",
                    "follower_chg_24h": f"{F['chg_24h'] * 100:.2f}%",
                    "lag_gap_%": f"{(L['chg_24h'] - F['chg_24h']) * 100:.2f}%"
                })

    return pd.DataFrame(followers)

def tp_sl(events, lead_gain, atr_pct):
    tp_pct = round(max(lead_gain * 0.5, 0.05), 4)
    sl_pct = round(max(atr_pct * 1.5, 0.03), 4)
    return {
        "tradeable": True,
        "tp_pct": f"{tp_pct * 100:.2f}%",
        "sl_pct": f"{sl_pct * 100:.2f}%",
        "risk_reward": round(tp_pct / sl_pct, 2) if sl_pct > 0 else 1.0
    }