import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone

st.set_page_config(
    page_title="BEKİROĞLU AI TRADER",
    page_icon="📈",
    layout="wide"
)

INITIAL_CASH = 1000.0
RISK_PER_TRADE = 0.005
MAX_POSITION_PCT = 0.25

ASSETS = {
    "ABD hisseleri": {
        "AAPL": "Apple",
        "MSFT": "Microsoft",
        "NVDA": "Nvidia",
        "AMZN": "Amazon",
        "ASTS": "AST SpaceMobile",
        "SPY": "S&P 500 ETF",
        "QQQ": "Nasdaq 100 ETF",
    },
    "Kripto": {
        "BTC-USD": "Bitcoin",
        "ETH-USD": "Ethereum",
        "SOL-USD": "Solana",
    },
    "Döviz": {
        "EURUSD=X": "EUR/USD",
        "GBPUSD=X": "GBP/USD",
    },
}

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
div[data-testid="stMetric"] {background: rgba(120,120,120,.07); padding: 12px; border-radius: 10px;}
.small-note {font-size: .85rem; color: #777;}
</style>
""", unsafe_allow_html=True)

st.title("📈 BEKİROĞLU AI TRADER")
st.caption("v1.0 · Çoklu piyasa tarayıcısı ve sanal işlem laboratuvarı")

st.warning(
    "Bu uygulama eğitim ve simülasyon içindir. Gerçek emir göndermez. "
    "Veriler gecikmeli, eksik veya hatalı olabilir; yatırım tavsiyesi değildir."
)

@st.cache_data(ttl=300, show_spinner=False)
def get_history(symbol):
    try:
        df = yf.download(
            symbol, period="6mo", interval="1d",
            auto_adjust=True, progress=False, threads=False
        )
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        needed = [c for c in ["Close", "High", "Low", "Volume"] if c in df.columns]
        return df[needed].dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def analyse(symbol, name):
    df = get_history(symbol)
    if df.empty or len(df) < 55:
        return None, df
    close = df["Close"].astype(float)
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    r = rsi(close)
    price = float(close.iloc[-1])
    rsi_now = float(r.iloc[-1]) if pd.notna(r.iloc[-1]) else np.nan
    e20 = float(ema20.iloc[-1])
    e50 = float(ema50.iloc[-1])

    if e20 > e50 and price > e20 and 45 <= rsi_now <= 68:
        signal = "AL sinyali"
    elif e20 < e50 or rsi_now >= 75:
        signal = "İzle / çıkış uyarısı"
    else:
        signal = "Bekle"

    row = {
        "Sembol": symbol,
        "Varlık": name,
        "Son fiyat": price,
        "RSI (14)": round(rsi_now, 1),
        "EMA 20": e20,
        "EMA 50": e50,
        "Sinyal": signal,
        "Günlük değişim %": float(close.pct_change().iloc[-1] * 100),
    }
    return row, df

if "cash" not in st.session_state:
    st.session_state.cash = INITIAL_CASH
if "positions" not in st.session_state:
    st.session_state.positions = {}
if "trades" not in st.session_state:
    st.session_state.trades = []
if "scan_results" not in st.session_state:
    st.session_state.scan_results = []
if "last_scan" not in st.session_state:
    st.session_state.last_scan = None

with st.sidebar:
    st.header("⚙️ Tarama ayarları")
    chosen_groups = st.multiselect(
        "Piyasa seç",
        list(ASSETS.keys()),
        default=list(ASSETS.keys())
    )
    st.caption("Tarama günlük mumlarla yapılır. Her 5 dakikada otomatik yenilenmez.")
    if st.button("🔄 Verileri yenile", use_container_width=True):
        get_history.clear()
        st.session_state.scan_results = []
        st.rerun()
    st.divider()
    st.markdown("**Sanal hesap kuralları**")
    st.write("Başlangıç: $1.000")
    st.write("İşlem başı planlanan risk: %0,5")
    st.write("Pozisyon üst sınırı: %25")
    st.write("Kaldıraç: Kapalı")

symbols = []
for group in chosen_groups:
    for symbol, name in ASSETS[group].items():
        symbols.append((symbol, name))

if not symbols:
    st.info("Tarama yapmak için sol menüden en az bir piyasa seç.")
else:
    if st.button("🚀 Piyasaları tara", type="primary", use_container_width=True):
        rows = []
        progress = st.progress(0)
        status = st.empty()
        for i, (symbol, name) in enumerate(symbols):
            status.write(f"Veri alınıyor: {symbol}")
            row, _ = analyse(symbol, name)
            if row:
                rows.append(row)
            progress.progress((i + 1) / len(symbols))
        st.session_state.scan_results = rows
        st.session_state.last_scan = datetime.now().strftime("%d.%m.%Y %H:%M")
        status.empty()
        progress.empty()

if st.session_state.last_scan:
    st.caption(f"Son tarama: {st.session_state.last_scan}")

rows = st.session_state.scan_results
if rows:
    df_results = pd.DataFrame(rows)
    st.subheader("🔎 Piyasa tarama sonuçları")
    display = df_results.copy()
    for col in ["Son fiyat", "EMA 20", "EMA 50"]:
        display[col] = display[col].map(lambda x: f"{x:,.4f}")
    display["Günlük değişim %"] = display["Günlük değişim %"].map(lambda x: f"{x:+.2f}%")
    st.dataframe(display, use_container_width=True, hide_index=True)
    buys = int((df_results["Sinyal"] == "AL sinyali").sum())
    st.caption(f"Tarama kapsamı: {len(df_results)} varlık · AL sinyali: {buys}. Sinyaller tek başına işlem gerekçesi değildir.")
else:
    st.info("Henüz tarama yapılmadı. 'Piyasaları tara' düğmesine dokun.")

st.divider()
st.subheader("💼 1.000 dolarlık sanal portföy")

# Latest available prices for held assets
market_values = {}
for symbol, pos in st.session_state.positions.items():
    _, hist = analyse(symbol, pos["name"])
    if not hist.empty:
        market_values[symbol] = float(hist["Close"].iloc[-1])
    else:
        market_values[symbol] = pos["avg_price"]

positions_value = sum(
    pos["qty"] * market_values.get(symbol, pos["avg_price"])
    for symbol, pos in st.session_state.positions.items()
)
equity = st.session_state.cash + positions_value
unrealized = sum(
    pos["qty"] * (market_values.get(symbol, pos["avg_price"]) - pos["avg_price"])
    for symbol, pos in st.session_state.positions.items()
)
realized = sum(t["Gerçekleşen kâr/zarar ($)"] for t in st.session_state.trades if t["Tür"] == "SATIŞ")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Nakit", f"${st.session_state.cash:,.2f}")
m2.metric("Portföy değeri", f"${positions_value:,.2f}")
m3.metric("Toplam özsermaye", f"${equity:,.2f}")
m4.metric("Açık pozisyon kâr/zararı", f"${unrealized:+,.2f}")

st.caption(f"Gerçekleşmiş satış kâr/zararı: ${realized:+,.2f} · Sanal hesap başlangıcı: $1.000")

st.markdown("#### Sanal işlem aç")
if rows:
    options = {f'{r["Sembol"]} — {r["Varlık"]}': r for r in rows}
else:
    options = {}
with st.form("buy_form"):
    selected_label = st.selectbox("Varlık", list(options.keys()) if options else ["Önce piyasa taraması yap"])
    units = st.number_input("Alınacak miktar", min_value=0.0, value=0.1, step=0.1, format="%.6f")
    buy_submit = st.form_submit_button("Sanal alım yap", type="primary", disabled=not bool(options))
    if buy_submit and options:
        item = options[selected_label]
        symbol = item["Sembol"]
        price = float(item["Son fiyat"])
        cost = units * price
        risk_budget = equity * RISK_PER_TRADE
        planned_stop = price * 0.975
        planned_risk = units * (price - planned_stop)
        max_value = equity * MAX_POSITION_PCT
        if units <= 0:
            st.error("Miktar sıfırdan büyük olmalı.")
        elif cost > st.session_state.cash:
            st.error("Yetersiz sanal nakit.")
        elif cost > max_value:
            st.error("Bu alım, %25 pozisyon üst sınırını aşıyor.")
        elif planned_risk > risk_budget + 0.01:
            st.error(f"Bu alımın planlanan %2,5 stop riski ${planned_risk:.2f}; işlem risk bütçesi yaklaşık ${risk_budget:.2f}. Miktarı azalt.")
        else:
            old = st.session_state.positions.get(symbol)
            if old:
                new_qty = old["qty"] + units
                avg = (old["qty"] * old["avg_price"] + cost) / new_qty
                old["qty"] = new_qty
                old["avg_price"] = avg
            else:
                st.session_state.positions[symbol] = {
                    "name": item["Varlık"], "qty": units, "avg_price": price
                }
            st.session_state.cash -= cost
            st.session_state.trades.append({
                "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Tür": "ALIŞ", "Sembol": symbol, "Miktar": units,
                "Fiyat ($/birim)": price, "Gerçekleşen kâr/zarar ($)": 0.0
            })
            st.success(f"Sanal alım kaydedildi: {units:g} {symbol}")
            st.rerun()

if st.session_state.positions:
    st.markdown("#### Açık pozisyonlar")
    for symbol, pos in list(st.session_state.positions.items()):
        price = market_values.get(symbol, pos["avg_price"])
        value = pos["qty"] * price
        pnl = pos["qty"] * (price - pos["avg_price"])
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{symbol}**")
        c2.write(f"Miktar: {pos['qty']:.6f}")
        c3.write(f"Değer: ${value:,.2f} · P/Z: ${pnl:+,.2f}")
        if c4.button("Sat", key=f"sell_{symbol}"):
            st.session_state.cash += value
            st.session_state.trades.append({
                "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Tür": "SATIŞ", "Sembol": symbol, "Miktar": pos["qty"],
                "Fiyat ($/birim)": price,
                "Gerçekleşen kâr/zarar ($)": pnl
            })
            del st.session_state.positions[symbol]
            st.rerun()
else:
    st.caption("Henüz açık sanal pozisyon yok.")

st.divider()
st.subheader("🧾 İşlem geçmişi")
if st.session_state.trades:
    st.dataframe(pd.DataFrame(st.session_state.trades).iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.caption("Henüz işlem yapılmadı.")

left, right = st.columns(2)
with left:
    if st.button("Sanal hesabı sıfırla", use_container_width=True):
        st.session_state.cash = INITIAL_CASH
        st.session_state.positions = {}
        st.session_state.trades = []
        st.rerun()
with right:
    if st.button("Tarama sonuçlarını temizle", use_container_width=True):
        st.session_state.scan_results = []
        st.session_state.last_scan = None
        st.rerun()

st.caption(
    "Veri kaynağı: Yahoo Finance üzerinden yfinance. Veri erişimi ve gecikme garanti edilmez. "
    "Sanal işlemler yalnızca açık uygulama oturumu boyunca saklanır; sayfa/oturum sıfırlanırsa kaybolabilir. "
    "Bu sürüm otomatik alım-satım, haber analizi veya gerçek borsa bağlantısı içermez."
)
