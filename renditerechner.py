import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

###############################################################################
# STREAMLIT-SEITENKONFIGURATION
###############################################################################
st.set_page_config(
    page_title="Renditerechner Clean",
    layout="wide"
)

###############################################################################
# TITEL & EINLEITUNG
###############################################################################
st.title("Berechnung der Rendite in drei Szenarien")
st.markdown("""
Willkommen zu deinem Renditerechner!  
Gib unten deine **Status Quo**-Daten ein und passe die **Zukunftsannahmen** an.  
Über den **Margin of Safety**-Schieberegler kannst du zusätzliche Sicherheit berücksichtigen.
""")

###############################################################################
# 1) STATUS QUO » DIE ZAHLEN HEUTE
###############################################################################
st.header("1) Status Quo » Die Zahlen heute")

col1, col2, col3, col4 = st.columns(4)

with col1:
    boersenwert = st.number_input("Börsenwert (Mrd.)", value=1056.0, step=1.0)
with col2:
    aktienkurs = st.number_input("Aktienkurs", value=131.0, step=1.0)
with col3:
    umsatz = st.number_input("Umsatz (Mrd.)", value=514.0, step=1.0)
with col4:
    aussch_q = st.number_input("Ausschüttungsquote (%)", value=0.0, step=1.0)

st.write("---")

###############################################################################
# 2) ZUKUNFT » ANNAHMEN ZUR WERTENTWICKLUNG
###############################################################################
st.header("2) Zukunft » Annahmen zur Wertentwicklung")
st.markdown("Die kurzfristigen Werte nähern sich über einen 10-Jahres-Horizont an die langfristigen an.")

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
    shyield_kurz = st.number_input("Shareholder Yield kurzf. (%)", value=1.0, step=0.5)
    shyield_lang = st.number_input("Shareholder Yield langfr. (%)", value=3.0, step=0.5)

margin_of_safety = st.slider("Margin of Safety (%)", min_value=0, max_value=50, value=20)

st.write("---")

###############################################################################
# 3) EINFACHE BEISPIEL-BERECHNUNG
###############################################################################
st.header("Ergebnisse in zwei Szenarien (kurzfristig vs. langfristig)")

# Vereinfachte Demo-Funktionen
def calc_fair_value(umsatz, marge, kgv):
    """Berechnet einen sehr vereinfachten 'fairen Wert' = (Umsatz*marge) * kgv."""
    net_income = umsatz * (marge / 100.0)
    return net_income * kgv

# Kurzfristig
fair_value_kurz = calc_fair_value(umsatz, nettomarge_kurz, kgv_kurz)
fair_value_kurz_mos = fair_value_kurz * (1 - margin_of_safety/100)

# Langfristig
fair_value_lang = calc_fair_value(umsatz, nettomarge_lang, kgv_lang)
fair_value_lang_mos = fair_value_lang * (1 - margin_of_safety/100)

# Shareholder Yield + Wertsteigerung (Pseudo)
# Angenommen, boersenwert*Mrd. => in echte Zahlen: boersenwert*1e9
# Hier nur als Demo: (fair_value / actual_value) -1 => Wachstumsfaktor
actual_value = boersenwert * 1e9  # Um Mrd. in "absolute" Zahlen zu wandeln
wertsteigerung_kurz = (fair_value_kurz / actual_value) - 1
wertsteigerung_lang = (fair_value_lang / actual_value) - 1

gesamtrendite_kurz = (wertsteigerung_kurz + (shyield_kurz / 100.0)) * 100
gesamtrendite_lang = (wertsteigerung_lang + (shyield_lang / 100.0)) * 100

# Tabellarische Übersicht
import pandas as pd

df_res = pd.DataFrame({
    "": ["Kurzfristig", "Langfristig"],
    "Wachstum (%)": [wachstum_kurz, wachstum_lang],
    "Nettomarge (%)": [nettomarge_kurz, nettomarge_lang],
    "KGV": [kgv_kurz, kgv_lang],
    "Shareholder Yield (%)": [shyield_kurz, shyield_lang],
    "Fair Value (o. MoS)": [fair_value_kurz, fair_value_lang],
    "Fair Value (m. MoS)": [fair_value_kurz_mos, fair_value_lang_mos],
    "Gesamtrendite (%)": [gesamtrendite_kurz, gesamtrendite_lang]
})

st.table(df_res)

st.markdown("""
**Hinweis**: Alle Berechnungen sind stark vereinfacht und dienen nur der Demonstration 
des Layouts. In der Realität würdest du DCF, Diskontierung, etc. berücksichtigen.
""")

st.write("---")

###############################################################################
# 4) GRAFISCHE DARSTELLUNG: BALKENDIAGRAMM
###############################################################################
st.subheader("Jährliche Renditeerwartung (Beispiel)")

labels = ["kurzfristig", "langfristig"]
renditen = [gesamtrendite_kurz, gesamtrendite_lang]

fig, ax = plt.subplots(figsize=(6,4))
bars = ax.bar(labels, renditen, color=["#1f77b4", "#ff7f0e"])
ax.set_ylabel("Rendite in %")
ax.set_title("Jährliche Renditeerwartung (vereinfacht)")
for i, bar in enumerate(bars):
    ax.text(
        bar.get_x() + bar.get_width()/2, 
        bar.get_height() + 0.5, 
        f"{renditen[i]:.1f}%", 
        ha="center"
    )
# Falls Renditen sehr negativ, Achse anpassen
ax.set_ylim([min(renditen)-5, max(renditen)+5])

st.pyplot(fig)

st.write("---")

###############################################################################
# ABSCHLUSS / DISCLAIMER
###############################################################################
st.markdown("""
**Disclaimer**:  
Dies ist ein vereinfachtes Modell und keine Anlageberatung. 
Die Werte sind Beispiele und dienen nur zur Illustration.
""")
