import pandas as pd

def calculate_atr(df, period=14):
    if df is None or df.empty or len(df) < 2:
        return 0.05
    
    # Ensure window is a valid integer and does not exceed available candles
    safe_period = int(max(1, min(period, len(df) - 1)))
    
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    atr = tr.rolling(window=safe_period, min_periods=1).mean()
    last_close = df['close'].iloc[-1]
    return float(atr.iloc[-1] / last_close) if last_close > 0 else 0.05

def analyze(df_tf, df_1d=None):
    if df_tf is None or df_tf.empty or len(df_tf) < 2:
        return {"atr_pct": 0.05, "htf_score": 50, "htf_aligned": False, "htf_late": False}
    
    close = df_tf['close']
    n = len(close)
    
    # Strictly cast rolling windows to integers
    w_fast = int(max(1, min(20, n)))
    w_slow = int(max(1, min(50, n)))
    
    sma_fast = close.rolling(window=w_fast, min_periods=1).mean().iloc[-1]
    sma_slow = close.rolling(window=w_slow, min_periods=1).mean().iloc[-1]
    
    cur_price = close.iloc[-1]
    atr_pct = calculate_atr(df_tf)
    
    aligned = bool(cur_price > sma_fast > sma_slow)
    late = bool(cur_price > sma_fast * 1.15)
    
    score = 50
    if aligned:
        score += 25
    if not late and aligned:
        score += 15
    if cur_price < sma_fast:
        score -= 20
        
    return {
        "atr_pct": round(atr_pct, 4),
        "htf_score": max(0, min(100, score)),
        "htf_aligned": aligned,
        "htf_late": late
    }