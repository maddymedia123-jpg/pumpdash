"""5 bull + 5 bear analysts debate over a numeric data packet; 1 head agent decides.
Agents never do math: they cite keys from the packet, and uncited claims are discarded."""
import json
import os

MIN_LIQ = 50_000

BULL = {
    "flow": "volume z-score, CVD, accumulation",
    "derivatives": "funding, open interest, liquidation clusters",
    "wallets": "smart-wallet and exchange-flow evidence",
    "rotation": "narrative / money-rotation fit and catalysts",
    "structure": "higher-timeframe market structure and patterns (BOS, squeeze, triangle, spring, breakout)",
}
BEAR = {
    "contract_risk": "mint rights, LP lock, taxes, holder concentration, honeypot signs",
    "late_entry": "extension, failed breakouts, overhead resistance on higher timeframes",
    "supply_overhang": "token unlocks, whale distribution, exchange inflows",
    "regime_manipulation": "BTC trend, wash volume, spoofing, pump-group behavior",
    "execution_risk": "depth, slippage, exit liquidity, spread",
}


def claude(prompt, model=os.getenv("PUMP_MODEL", "claude-sonnet-5-5")):
    import anthropic
    r = anthropic.Anthropic().messages.create(model=model, max_tokens=700,
                                              messages=[{"role": "user", "content": prompt}])
    return r.content[0].text


def _json(text):
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def run_agent(name, lens, side, packet, llm, opposing=None):
    prompt = (f"You are the {side.upper()} analyst. Focus: {lens}.\n"
              f"Use ONLY these data fields and cite their keys:\n{json.dumps(packet, default=str)}\n"
              + (f"Rebut or concede these opposing reports:\n{json.dumps(opposing)}\n" if opposing else "")
              + 'Reply JSON only: {"confidence":0-1,"claims":[{"text":str,"evidence_keys":[str]}],"invalidation":str}')
    try:
        rep = _json(llm(prompt))
    except Exception:
        rep = {"confidence": 0, "claims": [], "invalidation": "unparseable"}
    rep["claims"] = [c for c in rep.get("claims", [])
                     if c.get("evidence_keys") and all(k in packet for k in c["evidence_keys"])]
    return {"agent": name, "side": side, **rep}


def debate(packet, llm, rounds=2):
    reports = {"bull": [run_agent(n, l, "bull", packet, llm) for n, l in BULL.items()],
               "bear": [run_agent(n, l, "bear", packet, llm) for n, l in BEAR.items()]}
    for _ in range(rounds - 1):  # cross-examination round
        reports = {s: [run_agent(n, l, s, packet, llm, opposing=reports["bear" if s == "bull" else "bull"])
                       for n, l in team.items()] for s, team in (("bull", BULL), ("bear", BEAR))}
    return reports


def head(packet, reports, llm):
    prompt = ("You are the head analyst. Weigh the bull and bear reports; discount unsupported claims.\n"
              f"Packet: {json.dumps(packet, default=str)}\nReports: {json.dumps(reports)}\n"
              'Reply JSON only: {"verdict":"candidate|watch|reject","score":0-100,"summary":str}')
    try:
        out = _json(llm(prompt))
    except Exception:
        out = {"verdict": "reject", "score": 0, "summary": "head output unparseable"}
    # deterministic vetoes the LLM cannot override
    if packet.get("dex_liq_usd", 1e12) < MIN_LIQ:
        out["verdict"] = "reject"
    elif packet.get("htf_late") and out.get("verdict") == "candidate":
        out["verdict"] = "watch"
    return out