import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# Seitenkonfiguration
# ---------------------------------------------------------
st.set_page_config(layout="centered", page_title="Erweitertes Renditerechner-Tool")

# Optional: eigenes Theme via CSS (einfaches Beispiel)
st.markdown("""
<style>
/* Hintergrundfarbe */
body {
    background-color: #f8f9fa;
}
/* Überschriften-Stil */
h1, h2, h3 {
    color: #333333;
    font-family: "Arial", sans-serif;
}
/* Kartenähnliche Container */
.block-container {
    background-color: #ffffff;
    padding: 2rem 2rem 2rem 2rem;
    border-radius: 8px;
    box-shadow: 0px 0px 10px rgba(0,0,0,0.05);
}
/* Tabellenstil */
table {
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# TITEL
# ---------------------------------------------------------
st.title("Berechnung der Rendite in drei Szenarien")
st.markdown("""
### Status Quo » Die Zahlen heute
""")

# ---------------------------------------------------------
# 1) STATUS QUO EINGABEN
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    boersenwert = st.number_input("Börsenwert (Mrd.)", value=1056.0, step=1.0)
with col2:
    aktienkurs = st.number_input("Aktienkurs", value=131.0, step=1.0)
with col3:
    umsatz = st.number_input("Umsatz (Mrd.)", value=514.0, step=1.0)
with col4:
    ausschüttungsquote = st.number_input("Ausschüttungsquote (%)", value=0.0, step=1.0)

st.write("---")

# ---------------------------------------------------------
# 2) ZUKUNFTSANNAHMEN
# ---------------------------------------------------------
st.markdown("### Zukunft » Annahmen zur Wertentwicklung")

st.markdown("""
Die kurzfristigen Werte nähern sich über einen 10-Jahres-Horizont an die langfristigen an.
""")

colA, colB, colC, colD = st.columns(4)

with colA:
    wachstum_kurz = st.number_input("Wachstum kurzf. (%)", value=7.0, step=1.0)
    wachstum_lang = st.number_input("Wachstum langfr. (%)", value=14.0, step=1.0)
with colB:
    nettomarge_kurz = st.number_input("Nettomarge kurzf. (%)", value=4.0, step=1.0)
    nettomarge_lang = st.number_input("Nettomarge langfr. (%)", value=10.0, step=1.0)
with colC:
    kgv_kurz = st.number_input("KGV kurzf.", value=15.0, step=1.0)
    kgv_lang = st.number_input("KGV langfr.", value=25.0, step=1.0)
with colD:
    shareholder_yield_kurz = st.number_input("Shareholder Yield kurzf. (%)", value=1.0, step=1.0)
    shareholder_yield_lang = st.number_input("Shareholder Yield langfr. (%)", value=3.0, step=1.0)

margin_of_safety = st.slider("Margin of Safety (%)", min_value=0, max_value=50, value=20)

st.write("---")

# ---------------------------------------------------------
# 3) BERECHNUNGEN / TABELLE
#    -> Hier bauen wir eine Beispiel-Tabelle, die "kurzfristig" / "langfristig" anzeigt
# ---------------------------------------------------------
st.markdown("### Ergebnisse in zwei Szenarien (kurzfristig vs. langfristig)")

# Beispielhafte Berechnungen (sehr vereinfacht):
def calc_fair_value(umsatz, marge, kgv):
    # Netto-Gewinn
    net_income = umsatz * (marge / 100)
    # Fairer Wert = net_income * kgv
    return net_income * kgv

# Kurzfristig
fair_value_kurz = calc_fair_value(umsatz, nettomarge_kurz, kgv_kurz)
fair_value_kurz_mos = fair_value_kurz * (1 - margin_of_safety/100)

# Langfristig
fair_value_lang = calc_fair_value(umsatz, nettomarge_lang, kgv_lang)
fair_value_lang_mos = fair_value_lang * (1 - margin_of_safety/100)

# Shareholder Yield Einbeziehen (sehr vereinfacht):
# "Gesamtrendite" ~ Wertsteigerung + Shareholder Yield
# Hier rein exemplarisch:
wertsteigerung_kurz = (fair_value_kurz / (boersenwert*1e6)) - 1  # pseudo
wertsteigerung_lang = (fair_value_lang / (boersenwert*1e6)) - 1

gesamtrendite_kurz = (wertsteigerung_kurz + (shareholder_yield_kurz/100)) * 100
gesamtrendite_lang = (wertsteigerung_lang + (shareholder_yield_lang/100)) * 100

df_ergebnisse = pd.DataFrame({
    "": ["Kurzfristig", "Langfristig"],
    "Wachstum (%)": [wachstum_kurz, wachstum_lang],
    "Nettomarge (%)": [nettomarge_kurz, nettomarge_lang],
    "KGV": [kgv_kurz, kgv_lang],
    "Shareholder Yield (%)": [shareholder_yield_kurz, shareholder_yield_lang],
    "Fairer Wert (o. MoS)": [fair_value_kurz, fair_value_lang],
    "Fairer Wert (m. MoS)": [fair_value_kurz_mos, fair_value_lang_mos],
    "Gesamtrendite (%)": [gesamtrendite_kurz, gesamtrendite_lang]
})

st.table(df_ergebnisse)

st.markdown("""
**Hinweis**: Dies ist eine stark vereinfachte Darstellung. 
In der Realität würden hier komplexere Formeln für Wachstum, 
DCF-Berechnungen, Diskontierung, etc. verwendet.
""")

st.write("---")

# ---------------------------------------------------------
# 4) GRAFIK
#    -> Beispiel: Ein Balkendiagramm zur jährlichen Rendite
# ---------------------------------------------------------
st.markdown("### Jährl. Renditeerwartung in %")

labels = ["kurzfristig", "langfristig"]
renditen = [gesamtrendite_kurz, gesamtrendite_lang]

fig, ax = plt.subplots(figsize=(5,3))
ax.bar(labels, renditen, color=["#1f77b4", "#ff7f0e"])
ax.set_ylim([min(renditen)-5, max(renditen)+5])
ax.set_ylabel("Rendite in %")
for i, v in enumerate(renditen):
    ax.text(i, v + 0.5, f"{v:.1f}%", ha="center")
ax.set_title("Jährliche Renditeerwartung (Beispiel)")

st.pyplot(fig)

st.write("---")

# ---------------------------------------------------------
# ABSCHLUSS
# ---------------------------------------------------------
st.markdown("""
**Disclaimer**: 
Keine Garantie für die Zukunft. 
Dieses Beispiel soll nur das Layout demonstrieren und ersetzt 
keine professionelle Anlageberatung.
""")
