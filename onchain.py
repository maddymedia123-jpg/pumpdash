import requests

def analyze(symbol, chain=None, pair=None):
    base_symbol = symbol.split("/")[0].upper()
    
    try:
        # DexScreener Public API (Free, no API key required)
        url = f"https://api.dexscreener.com/latest/dex/search?q={base_symbol}"
        r = requests.get(url, timeout=5)
        
        if r.status_code == 200:
            data = r.json()
            pairs = data.get("pairs", [])
            
            # Filter for USDT pairs to find the most accurate match
            valid_pairs = [p for p in pairs if p.get("quoteToken", {}).get("symbol") == "USDT" and p.get("baseToken", {}).get("symbol") == base_symbol]
            
            if not valid_pairs and pairs:
                valid_pairs = pairs # fallback to any pair found

            if valid_pairs:
                # Pick the pair with the highest liquidity
                best_pair = max(valid_pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0) or 0)
                
                liq_usd = float(best_pair.get("liquidity", {}).get("usd", 100000.0) or 100000.0)
                
                # Calculate buyer/seller transaction imbalance from 1h txns
                txns = best_pair.get("txns", {}).get("h1", {"buys": 0, "sells": 0})
                buys = txns.get("buys", 0)
                sells = txns.get("sells", 0)
                total_txns = buys + sells
                
                if total_txns > 0:
                    imbalance = round((buys - sells) / total_txns, 4)
                else:
                    imbalance = 0.0

                # Proxy wash share estimation based on volume-to-liquidity anomalies
                vol_24h = float(best_pair.get("volume", {}).get("h24", 0.0) or 0.0)
                wash_share = 0.05 if vol_24h > (liq_usd * 10) else 0.01

                return {
                    "imbalance": imbalance,
                    "wash_share": wash_share,
                    "dex_liq_usd": liq_usd
                }
    except Exception:
        pass

    # Default fallback if request fails
    return {
        "imbalance": 0.0,
        "wash_share": 0.0,
        "dex_liq_usd": 100000.0
    }
