"""Read-only dashboard for private paper trading data."""
import os
import streamlit as st
import pandas as pd
from store import read_state
from engine import equity, INITIAL, WATCH_ONLY

st.set_page_config(page_title="BEKİROĞLU AI TRADER 2.0", page_icon="📈", layout="wide")
st.title("📈 BEKİROĞLU AI TRADER 2.0")
st.caption("Otomatik sanal işlem · GitHub Actions + Supabase · Gerçek emir YOK")
st.warning("Bu sürüm kural tabanlıdır, yapay zekâ ile haber analizi içermez. Kâr garantisi yoktur. Fiyatlar gecikebilir. Sanal stoplar piyasa fiyatından farklı gerçekleşebilir.")
try:
    # Streamlit Cloud secrets are environment variables; never expose keys in UI.
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        st.error("DASHBOARD_PASSWORD secret eksik. Kurulum kılavuzunu kontrol et.")
        st.stop()
    entered = st.text_input("Kontrol paneli şifresi", type="password")
    if entered != password:
        st.info("Portföyü görmek için şifreni gir.")
        st.stop()
    if st.button("🔄 Verileri yenile"):
        st.rerun()
    state = read_state()
    if not state:
        st.info("İlk otomatik tarama henüz gerçekleşmedi. GitHub Actions > Run workflow çalıştır.")
        st.stop()
    total = equity(state)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam sanal bakiye", f"${total:,.2f}", f"${total - INITIAL:+,.2f}")
    c2.metric("Nakit", f"${state['cash']:,.2f}")
    c3.metric("Açık pozisyon", len(state["positions"]))
    c4.metric("İşlem kaydı", len(state["trades"]))
    st.caption(f"Son otomatik çalışma (UTC): {state.get('last_run') or 'Henüz yok'}")
    if state.get("halted"):
        st.error("Risk kilidi etkin: " + str(state.get("halt_reason")))
    if state.get("last_error"):
        st.error("Son işlem hatası: " + state["last_error"])
    st.subheader("Açık sanal pozisyonlar")
    if state["positions"]:
        rows = []
        for symbol, pos in state["positions"].items():
            px = float(state["last_prices"].get(symbol, pos["entry"]))
            rows.append({"Sembol": symbol, "Miktar": pos["qty"], "Giriş ($)": pos["entry"],
                         "Son fiyat ($)": px, "Stop ($)": pos["stop"],
                         "K/Z ($)": round(pos["qty"] * (px - pos["entry"]), 2)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("Açık pozisyon yok.")
    st.subheader("Son sinyaller")
    signals = state.get("last_signals", {})
    if signals:
        rows = [{"Sembol": symbol, "Fiyat": v["price"], "RSI": v["rsi"],
                 "Sinyal": v["signal"], "Veri tarihi": v["bar_date"],
                 "İşlem izni": "Sadece izle" if symbol in WATCH_ONLY else "Sanal"}
                for symbol, v in signals.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.subheader("İşlem geçmişi")
    if state["trades"]:
        st.dataframe(pd.DataFrame(state["trades"][::-1]), hide_index=True, use_container_width=True)
        st.download_button("CSV indir", pd.DataFrame(state["trades"]).to_csv(index=False).encode("utf-8-sig"),
                           file_name="sanal_islemler.csv", mime="text/csv")
    else:
        st.info("Henüz işlem kaydı yok.")
    st.caption("GitHub Actions zamanlaması garanti değildir; servisler uyuyabilir/gecikebilir. Günlük kapanış verileriyle çalışır; gerçek zamanlı fiyat veya 7/24 kesin çalışma garantisi yoktur.")
except Exception as exc:
    st.error("Veri okunamadı. Supabase bağlantısını ve secrets ayarlarını kontrol et.")
    st.caption(type(exc).__name__)
