import pandas as pd

def find_followers(u, leader_chg=0.15, leader_relvol=1.5):
    """Finds lagger/follower coins in categories where a leader has already pumped."""
    # Convert list to DataFrame if necessary
    if isinstance(u, list):
        u = pd.DataFrame(u)
        
    if u.empty:
        return pd.DataFrame()
        
    # Ensure required columns exist
    if "chg_24h" not in u.columns:
        u["chg_24h"] = 0.0
    if "rel_vol" not in u.columns:
        u["rel_vol"] = 1.0

    followers = []
    leaders = u[(u["chg_24h"] >= leader_chg) & (u["rel_vol"] >= leader_relvol)]
    
    for _, L in leaders.iterrows():
        cat = L.get("category", "General")
        same_cat = u[(u["category"] == cat) & (u["symbol"] != L["symbol"])]
        for _, F in same_cat.iterrows():
            if F["chg_24h"] < L["chg_24h"]:
                followers.append({
                    "symbol": F["symbol"],
                    "category": cat,
                    "leader": L["symbol"],
                    "leader_chg_24h": L["chg_24h"],
                    "follower_chg_24h": F["chg_24h"]
                })
                
    return pd.DataFrame(followers)


def tp_sl(events, lead_gain, atr_pct):
    """Calculates take-profit and stop-loss targets based on category analogs."""
    if not events:
        return {
            "tradeable": False, 
            "tp_pct": round(lead_gain * 0.5, 4), 
            "sl_pct": round(atr_pct * 1.5, 4), 
            "reason": "Insufficient analog historical events"
        }
    
    return {
        "tradeable": True, 
        "tp_pct": round(lead_gain * 0.5, 4), 
        "sl_pct": round(atr_pct * 1.5, 4)
    }