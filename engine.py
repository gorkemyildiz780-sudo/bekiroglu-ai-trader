"""Rule-based PAPER trading engine. NEVER places broker orders."""
from datetime import datetime, timezone
import math
import yfinance as yf
import pandas as pd
from store import read_state, write_state

INITIAL = 1000.0
TRADE_RISK = 0.005
STOP_PCT = 0.025
MAX_POSITION = 0.25
MAX_POSITIONS = 3
DAILY_LIMIT = 0.015
WEEKLY_LIMIT = 0.03
DRAWDOWN_LIMIT = 0.08
# Stocks and spot crypto are denominated in USD; forex is WATCH-ONLY.
TRADABLE = {"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia",
            "ASTS": "AST SpaceMobile", "SPY": "S&P 500 ETF",
            "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana"}
WATCH_ONLY = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDTRY=X": "USD/TRY"}


def initial_state():
    return {"cash": INITIAL, "positions": {}, "trades": [], "last_prices": {},
            "last_signals": {}, "peak_equity": INITIAL, "day_anchor": None,
            "week_anchor": None, "last_run": None, "last_error": None,
            "halted": False, "halt_reason": None}


def bars(symbol):
    try:
        df = yf.download(symbol, period="6mo", interval="1d", auto_adjust=True,
                         progress=False, threads=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Close"])
        return df if len(df) >= 55 else None
    except Exception:
        return None


def signal(df):
    close = df["Close"].astype(float)
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    loss = float(down.iloc[-1])
    gain = float(up.iloc[-1])
    rsi = 100.0 if loss == 0 and gain > 0 else (50.0 if loss == 0 else 100 - 100 / (1 + gain / loss))
    price = float(close.iloc[-1])
    if not math.isfinite(price) or price <= 0:
        return None
    bullish = price > float(ema20.iloc[-1]) > float(ema50.iloc[-1]) and 45 <= rsi <= 68
    bearish = price < float(ema20.iloc[-1]) or float(ema20.iloc[-1]) < float(ema50.iloc[-1]) or rsi >= 75
    return {"price": round(price, 8), "rsi": round(rsi, 1),
            "signal": "AL" if bullish else ("SAT/BEKLE" if bearish else "BEKLE"),
            "bar_date": str(df.index[-1].date())}


def equity(state):
    return float(state["cash"]) + sum(float(p["qty"]) * float(state["last_prices"].get(s, p["entry"]))
                                          for s, p in state["positions"].items())


def record(state, side, symbol, qty, price, pnl=0):
    state["trades"].append({"at": datetime.now(timezone.utc).isoformat(), "side": side,
                            "symbol": symbol, "qty": round(qty, 8), "price": round(price, 8),
                            "pnl": round(pnl, 4)})
    state["trades"] = state["trades"][-1000:]


def close_position(state, symbol, price, reason):
    pos = state["positions"].pop(symbol)
    qty = float(pos["qty"])
    pnl = qty * (price - float(pos["entry"]))
    state["cash"] += qty * price
    record(state, "SAT: " + reason, symbol, qty, price, pnl)


def run_once():
    state = read_state() or initial_state()
    now = datetime.now(timezone.utc)
    day = now.date().isoformat()
    iso = now.isocalendar()
    week = f"{iso.year}-W{iso.week:02d}"
    try:
        observations = {}
        for symbol in {**TRADABLE, **WATCH_ONLY}:
            df = bars(symbol)
            if df is not None:
                item = signal(df)
                if item:
                    observations[symbol] = item
                    state["last_prices"][symbol] = item["price"]
        if not observations:
            raise RuntimeError("No market data received; no trades executed")
        state["last_signals"] = observations
        # Anchor at first observation in a new UTC day/week.
        before = equity(state)
        if not state["day_anchor"] or state["day_anchor"]["key"] != day:
            state["day_anchor"] = {"key": day, "equity": before}
        if not state["week_anchor"] or state["week_anchor"]["key"] != week:
            state["week_anchor"] = {"key": week, "equity": before}
        state["peak_equity"] = max(float(state["peak_equity"]), before)
        # Exit logic runs even when new entries are blocked.
        for symbol in list(state["positions"]):
            obs = observations.get(symbol)
            if not obs:
                continue
            pos = state["positions"][symbol]
            price = obs["price"]
            if price <= float(pos["stop"]):
                close_position(state, symbol, price, "STOP (simulated close)")
            elif obs["signal"] == "SAT/BEKLE":
                close_position(state, symbol, price, "trend exit")
        current = equity(state)
        daily_loss = current < float(state["day_anchor"]["equity"]) * (1 - DAILY_LIMIT)
        weekly_loss = current < float(state["week_anchor"]["equity"]) * (1 - WEEKLY_LIMIT)
        drawdown = current < float(state["peak_equity"]) * (1 - DRAWDOWN_LIMIT)
        if drawdown:
            state["halted"] = True
            state["halt_reason"] = "Max drawdown reached; manual reset required"
        blocked = state["halted"] or daily_loss or weekly_loss
        # One BUY per symbol per daily candle; avoids repeated 30-min entries.
        bought_bars = {(t["symbol"], t.get("bar_date")) for t in state["trades"]
                       if t["side"] == "AL"}
        if not blocked:
            for symbol in TRADABLE:
                if len(state["positions"]) >= MAX_POSITIONS:
                    break
                obs = observations.get(symbol)
                if not obs or obs["signal"] != "AL" or symbol in state["positions"]:
                    continue
                if (symbol, obs["bar_date"]) in bought_bars:
                    continue
                price = obs["price"]
                total = equity(state)
                qty = min(total * TRADE_RISK / (price * STOP_PCT),
                          total * MAX_POSITION / price, state["cash"] / price)
                qty = math.floor(qty * 1e6) / 1e6
                if qty <= 0:
                    continue
                cost = qty * price
                state["cash"] -= cost
                state["positions"][symbol] = {"qty": qty, "entry": price,
                                               "stop": round(price * (1 - STOP_PCT), 8),
                                               "bar_date": obs["bar_date"]}
                record(state, "AL", symbol, qty, price)
                state["trades"][-1]["bar_date"] = obs["bar_date"]
        state["last_error"] = None
    except Exception as exc:
        state["last_error"] = str(exc)[:300]
        # Avoid masking errors from automation logs.
        state["last_run"] = now.isoformat()
        write_state(state)
        raise
    state["last_run"] = now.isoformat()
    write_state(state)
    print(f"Paper cycle complete: {len(observations)} symbols, equity=${equity(state):.2f}, positions={len(state['positions'])}")


if __name__ == "__main__":
    run_once()
