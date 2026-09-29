import data

def score(pk, is_follower=False):
    s = pk.get("htf_score", 50)
    if pk.get("htf_aligned"):
        s += 15
    if pk.get("htf_late"):
        s -= 10
    if is_follower:
        s += 10
    return s

def scan(symbols, followers=None, timeframe="1h"):
    if followers is None:
        followers = set()
    packets = []
    for sym in symbols:
        try:
            pk = data.build_packet(sym, timeframe=timeframe)
            pk["scan_score"] = score(pk, sym in followers)
            packets.append(pk)
        except Exception as e:
            packets.append({"symbol": sym, "error": str(e)})
    return packets