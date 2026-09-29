import os
import pandas as pd
import streamlit as st

import agents
import data
import events
import rotation
import scan
import tracker

st.set_page_config(layout="wide", page_title="Pump Desk")
st.title("Pump Desk")
st.caption("Automated Crypto Research & Scanning Desk")

CATS, EV = "categories.csv", "events.csv"

# Load default watchlist from categories.csv if present
if os.path.exists(CATS):
    _c = pd.read_csv(CATS)
    cat_of = dict(zip(_c.symbol, _c.category))
    default_watch = "\n".join(_c.symbol.tolist())
else:
    cat_of = {}
    default_watch = "SOL/USDT\nTAO/USDT\nFET/USDT\nPEPE/USDT\nWIF/USDT\nSUI/USDT\nPENDLE/USDT"

sb = st.sidebar
watch = [s.strip() for s in sb.text_area("Watchlist (one per line)", default_watch, height=220).splitlines() if s.strip()]
auto_run = sb.checkbox("Auto-scan on launch", value=True)
use_llm = sb.toggle("Run agent debate on top picks", value=bool(os.getenv("ANTHROPIC_API_KEY")))
top_n = sb.slider("Top N sent to agents", 1, 5, 2)


@st.cache_data(ttl=300, show_spinner=False)
def followers_now():
    if not cat_of:
        return set()
    return set(rotation.find_followers(data.universe(CATS)).get("symbol", []))


def render_verdict(pk, reports, v):
    st.subheader(f"{pk['symbol']}: {v.get('verdict')} ({v.get('score')})")
    st.write(v.get("summary"))
    bull, bear = st.columns(2)
    for col, side in ((bull, "bull"), (bear, "bear")):
        col.markdown(f"**{side.upper()} team**")
        for r in reports[side]:
            with col.expander(f"{r['agent']} (conf {r.get('confidence')})"):
                st.json(r)


def run_agents(pk):
    with st.spinner(f"Agents debating {pk['symbol']}..."):
        try:
            rep = agents.debate(pk, agents.claude)
            return rep, agents.head(pk, rep, agents.claude)
        except Exception as e:
            st.error(f"Agent run failed: {e}")
            return None, {"verdict": "scan"}


def execute_scan():
    with st.spinner(f"Scanning {len(watch)} coins across multi-exchanges..."):
        pks = scan.scan(watch, followers_now())
    for p in pks:
        if "error" in p:
            st.warning(f"{p['symbol']}: {p['error']}")
    ok = sorted((p for p in pks if "error" not in p), key=lambda p: p["scan_score"], reverse=True)
    cols = ["symbol", "scan_score", "htf_score", "htf_aligned", "htf_late", "deriv_regime", "deriv_funding",
            "chain_imbalance", "chain_wash_share", "dex_liq_usd"]
    if ok:
        st.dataframe(pd.DataFrame(ok).reindex(columns=cols), use_container_width=True)
    for p in ok:
        data.log_signal(p, {"verdict": "scan"})
    if use_llm:
        for p in [p for p in ok if p["scan_score"] > 0][:top_n]:
            rep, v = run_agents(p)
            if rep:
                data.log_signal(p, v)
                render_verdict(p, rep, v)


t_scan, t_dive, t_rot, t_bt, t_trk = st.tabs(["Scan", "Deep dive", "Rotation", "Backtest", "Tracker"])

with t_scan:
    btn = st.button("Scan watchlist")
    if btn or auto_run:
        execute_scan()

with t_dive:
    sym = st.text_input("Symbol", "SOL/USDT")
    c1, c2 = st.columns(2)
    chain, pair = c1.text_input("DEX chain (optional)"), c2.text_input("Pool address (optional override)")
    lead = st.number_input("Current leader 24h gain % (for rotation TP)", 0.0, 500.0, 30.0) / 100
    if st.button("Analyze"):
        try:
            pk = data.build_packet(sym, chain or None, pair or None)
        except Exception as e:
            st.error(f"Could not build packet: {e}")
            st.stop()
        pk["scan_score"] = scan.score(pk, sym in followers_now())
        m = st.columns(4)
        m[0].metric("Scan score", pk["scan_score"])
        m[1].metric("HTF score", pk["htf_score"])
        m[2].metric("HTF aligned", str(pk["htf_aligned"]))
        m[3].metric("Late-entry", str(pk["htf_late"]))
        st.dataframe(pd.Series(pk).astype(str).rename("value"), use_container_width=True)
        v = {"verdict": "scan"}
        if use_llm:
            rep, v = run_agents(pk)
            if rep:
                render_verdict(pk, rep, v)
        ev = pd.read_csv(EV) if os.path.exists(EV) else pd.DataFrame()
        if len(ev) and cat_of.get(sym) in set(ev.category):
            ev = ev[ev.category == cat_of[sym]]
        lv = rotation.tp_sl(ev.to_dict("records"), lead, pk["4h_atr_pct"])
        st.subheader("TP / SL (% from entry)")
        st.json(lv)
        data.log_signal(pk, v)

with t_rot:
    if cat_of and st.button("Scan rotation"):
        try:
            f = rotation.find_followers(data.universe(CATS))
            st.dataframe(f if len(f) else pd.DataFrame({"result": ["no leader/follower pairs right now"]}))
        except Exception as e:
            st.error(f"Rotation scan failed: {e}")

with t_bt:
    days = st.slider("History (days)", 30, 180, 120)
    if cat_of and st.button("Build event history (slow)"):
        with st.spinner("Downloading history and extracting events..."):
            built = events.build(CATS, days)
            built.to_csv(EV, index=False)
    if os.path.exists(EV):
        ev = pd.read_csv(EV)
        if len(ev):
            st.dataframe(events.edge(ev), use_container_width=True)
            st.dataframe(ev.tail(200), use_container_width=True)

with t_trk:
    if st.button("Evaluate matured signals (72h+ old)"):
        with st.spinner("Scoring logged signals..."):
            res = tracker.evaluate()
        if res.empty:
            st.info("No matured signals yet.")
        else:
            st.dataframe(tracker.summary(res), use_container_width=True)
            st.dataframe(res, use_container_width=True)