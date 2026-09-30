import json
import re

def _json(text):
    """Robust JSON parser that strips markdown code blocks and extracts valid JSON."""
    if not text:
        return {}
    try:
        text_str = str(text).strip()
        
        # Strip markdown code blocks if the LLM wrapped them
        if "```" in text_str:
            text_str = re.sub(r"^```(?:json)?\s*", "", text_str)
            text_str = re.sub(r"\s*```$", "", text_str)
            text_str = text_str.strip()
            
        return json.loads(text_str)
    except Exception:
        # Fallback: extract substring between first '{' and last '}'
        try:
            start = text_str.index('{')
            end = text_str.rindex('}') + 1
            return json.loads(text_str[start:end])
        except Exception:
            return {}

def evaluate_packet(packet):
    """
    Evaluates market packets through bull and bear analytical lenses.
    Returns structured arguments, confidence levels, and final verdicts.
    """
    symbol = packet.get("symbol", "UNKNOWN")
    htf_score = packet.get("htf_score", 50)
    deriv_regime = packet.get("deriv_regime", "neutral")
    funding = packet.get("deriv_funding", 0.0)
    imbalance = packet.get("chain_imbalance", 0.0)
    
    # Generate structured bull and bear arguments based on packet metrics
    bull_conf = min(max(int(htf_score * 0.7 + (15 if "bullish" in deriv_regime else 0)), 10), 95)
    bear_conf = min(max(int((100 - htf_score) * 0.7 + (15 if "overheated" in deriv_regime else 0)), 10), 95)
    
    bull_team = {
        "flow": {"conf": bull_conf, "note": f"DEX imbalance stands at {imbalance}, showing active accumulation."},
        "derivatives": {"conf": bull_conf, "note": f"Derivative regime is currently labeled as {deriv_regime}."},
        "wallets": {"conf": max(bull_conf - 10, 10), "note": "Holder distribution stable across liquid pools."},
        "rotation": {"conf": bull_conf, "note": "Capital rotation favorable for category momentum."},
        "structure": {"conf": htf_score, "note": f"Higher timeframe structure score is robust at {htf_score}."}
    }
    
    bear_team = {
        "contract_risk": {"conf": bear_conf, "note": "Standard smart contract risk applies to DEX liquidity pools."},
        "late_entry": {"conf": bear_conf, "note": "Caution required against chasing extended momentum."},
        "supply_overhang": {"conf": max(bear_conf - 5, 10), "note": f"Funding rate is currently tracking at {funding}."},
        "regime_manipulation": {"conf": bear_conf, "note": "Watch for sudden volatility swings in perp markets."},
        "execution_risk": {"conf": bear_conf, "note": "Slippage parameters should be maintained during execution."}
    }
    
    # Determine verdict based on scores
    if bull_conf >= bear_conf:
        verdict = "approve"
        overall_conf = bull_conf
    else:
        verdict = "reject"
        overall_conf = bear_conf

    return {
        "symbol": symbol,
        "verdict": verdict,
        "confidence": overall_conf,
        "bull_team": bull_team,
        "bear_team": bear_team
    }
