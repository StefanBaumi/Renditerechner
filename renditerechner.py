import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

st.set_page_config(layout="centered")
st.title("Erweitertes Renditerechner-Tool")

###############################################################################
#  HILFSFUNKTIONEN ZUR BERECHNUNG
###############################################################################

def project_kgv_scenario(
    start_revenue,
    start_shares,
    start_net_margin,     # in %
    annual_revenue_growth,
    annual_dilution,      # in %
    future_pe,
    discount_rate,        # in %
    margin_of_safety,     # in %
    years
):
    """
    KGV-Ansatz (pro Jahr):
      1) Umsatz wächst mit annual_revenue_growth %
      2) Nettomarge (start_net_margin) bleibt hier als Konstante
      3) Netto-Gewinn = Umsatz * (net_margin/100)
      4) Aktienanzahl ändert sich um annual_dilution % p.a.
      5) EPS = Netto-Gewinn / Aktienanzahl
      6) Am Ende: Market Cap = (Gewinn in Jahr X) * future_pe
         => Kurs in Jahr X = Market Cap / Aktienanzahl
      7) Diskontierung auf heute
      8) Margin of Safety abziehen

    Rückgabe:
      - df (DataFrame) mit Verlauf von Jahr zu Jahr (Umsatz, Gewinn, Shares, EPS, FCF=0 hier)
      - fair_price_today (ohne MoS)
      - fair_price_mos (mit MoS)
    """
    # Jährliche Faktoren
    g = 1 + annual_revenue_growth / 100.0
    d = 1 + annual_dilution / 100.0
    r = 1 + discount_rate / 100.0
    
    # Startwerte
    revenue = start_revenue
    shares = start_shares
    net_margin_decimal = start_net_margin / 100.0

    # Für die grafische Darstellung speichern wir pro Jahr die Werte
    records = []
    
    for year in range(0, years+1):
        # Gewinn
        net_income = revenue * net_margin_decimal
        # EPS
        eps = net_income / shares if shares > 0 else 0.0

        records.append({
            "Jahr": year,
            "Umsatz": revenue,
            "NetIncome": net_income,
            "Shares": shares,
            "EPS": eps,
            "FCF": 0.0  # Im KGV-Modell ignorieren wir FCF; nur für Diagramm-Konsistenz
        })
        
        # Nächste Periode
        revenue *= g
        shares *= d

    # Letztes Jahr: Market Cap = NetIncome * future_pe
    final_net_income = records[-1]["NetIncome"]
    final_shares = records[-1]["Shares"]
    if final_shares > 0:
        final_market_cap = final_net_income * future_pe
        future_price = final_market_cap / final_shares
    else:
        future_price = 0.0

    # Diskontierung
    fair_price_today = future_price / (r ** years)

    # Margin of Safety
    mos_factor = 1 - margin_of_safety / 100.0
    fair_price_mos = fair_price_today * mos_factor

    df = pd.DataFrame(records)
    return df, fair_price_today, fair_price_mos


def project_dcf_scenario(
    start_revenue,
    start_shares,
    start_net_margin,     # in %
    fcf_margin,           # in %
    annual_revenue_growth,
    annual_dilution,      # in %
    discount_rate,        # in %
    terminal_growth,      # in %
    margin_of_safety,     # in %
    years
):
    """
    Vereinfachter DCF-Ansatz (pro Jahr):
      1) Umsatz wächst mit annual_revenue_growth %
      2) Nettomarge bleibt konstant
      3) Netto-Gewinn = Umsatz * (net_margin/100)
      4) FCF = Umsatz * (fcf_margin/100) (vereinfachte Annahme)
      5) Aktienanzahl ändert sich um annual_dilution % p.a.
      6) Jedes Jahr FCF diskontieren und aufsummieren
      7) Terminal Value: FCF im letzten Jahr * (1+terminal_growth/100) / (WACC - terminal_growth)
         und diskontieren
      8) Unternehmenswert = Summe aller diskontierten FCF + diskontierter Terminal Value
         => Aktienkurs = Unternehmenswert / Aktienanzahl letzter Periode
      9) Margin of Safety

    Rückgabe:
      - df (DataFrame) mit Verlauf pro Jahr (Umsatz, NetIncome, Shares, EPS, FCF)
      - fair_price_today (ohne MoS)
      - fair_price_mos (mit MoS)
    """
    g = 1 + annual_revenue_growth / 100.0
    d = 1 + annual_dilution / 100.0
    r = 1 + discount_rate / 100.0

    net_margin_decimal = start_net_margin / 100.0
    fcf_margin_decimal = fcf_margin / 100.0

    revenue = start_revenue
    shares = start_shares

    records = []
    npv = 0.0  # Net Present Value aller FCFs

    for year in range(1, years+1):
        # Update (Wachstum) am Anfang jeder Periode
        revenue *= g
        shares *= d

        # Gewinn und FCF in diesem Jahr
        net_income = revenue * net_margin_decimal
        fcf = revenue * fcf_margin_decimal

        # Diskontierung des FCF
        discounted_fcf = fcf / (r ** year)
        npv += discounted_fcf

        eps = net_income / shares if shares > 0 else 0.0

        records.append({
            "Jahr": year,
            "Umsatz": revenue,
            "NetIncome": net_income,
            "Shares": shares,
            "EPS": eps,
            "FCF": fcf
        })

    # Terminal Value am Ende von "years"
    if (discount_rate > terminal_growth):
        # Letzter FCF
        fcf_last = records[-1]["FCF"] if records else 0.0
        tv = fcf_last * (1 + terminal_growth/100.0) / ((discount_rate/100.0) - (terminal_growth/100.0))
        # Auf heute diskontieren
        tv_pv = tv / (r ** years)
    else:
        tv_pv = 0.0

    total_value = npv + tv_pv

    # Aktienanzahl am Ende
    final_shares = records[-1]["Shares"] if records else start_shares

    if final_shares > 0:
        fair_price_today = total_value / final_shares
    else:
        fair_price_today = 0.0

    mos_factor = 1 - margin_of_safety / 100.0
    fair_price_mos = fair_price_today * mos_factor

    df = pd.DataFrame(records)
    return df, fair_price_today, fair_price_mos


###############################################################################
#  1) BASISDATEN EINGEBEN
###############################################################################
st.header("1) Basisdaten laden")

ticker = st.text_input("Aktien-Ticker (z.B. AAPL):", "AAPL")

try:
    data = yf.Ticker(ticker).info
    current_price = data.get("regularMarketPrice", 150.0)
    market_cap = data.get("marketCap", 2e11)
    revenue_ttm = data.get("totalRevenue", 5e10)   # Umsatz TTM
    net_income_ttm = data.get("netIncomeToCommon", 5e9)
    shares_outstanding = data.get("sharesOutstanding", market_cap/current_price)
except:
    st.warning("Fehler beim Laden der Daten. Verwende Defaultwerte.")
    current_price = 150.0
    market_cap = 2e11
    revenue_ttm = 5e10
    net_income_ttm = 5e9
    shares_outstanding = market_cap / current_price

col1, col2, col3 = st.columns(3)
with col1:
    st.write(f"**Aktueller Kurs:** {current_price:.2f} USD")
with col2:
    st.write(f"**Marktkap.:** {market_cap/1e9:.2f} Mrd. USD")
with col3:
    st.write(f"**Aktienanzahl:** {shares_outstanding/1e6:.2f} Mio.")

st.write(f"**Umsatz (TTM):** {revenue_ttm/1e9:.2f} Mrd. USD")
st.write(f"**Gewinn (TTM):** {net_income_ttm/1e9:.2f} Mrd. USD")

###############################################################################
#  2) METHODENWAHL (KGV ODER DCF)
###############################################################################
valuation_method = st.radio(
    "Bewertungsmethode wählen:",
    ("KGV-Ansatz", "DCF-Ansatz")
)

###############################################################################
#  3) SZENARIEN-EINGABE (BEST, BASE, WORST)
###############################################################################
st.header("2) Szenarien (Best, Base, Worst)")

scenario_names = ["Best", "Base", "Worst"]
scenario_data = {}

col_scenarios = st.columns(3)
for i, scenario in enumerate(scenario_names):
    with col_scenarios[i]:
        st.subheader(f"{scenario} Case")
        
        # Umsatzwachstum
        revenue_growth = st.number_input(
            f"{scenario} Umsatzwachstum (%)", 
            value=10.0 + (5*(2 - i)),  # nur als Beispiel
            key=f"rev_growth_{scenario}"
        )
        # Nettomarge
        net_margin = st.number_input(
            f"{scenario} Nettomarge (%)",
            value= (net_income_ttm/revenue_ttm*100) if revenue_ttm>0 else 10.0,
            key=f"net_margin_{scenario}"
        )
        # Verwässerung / Rückkäufe
        dilution = st.number_input(
            f"{scenario} Verwässerung (+) / Rückkäufe (-) (% p.a.)", 
            value=0.0,
            key=f"dilution_{scenario}"
        )
        # Diskontierungsrate
        discount = st.number_input(
            f"{scenario} Diskontierungsrate (%)",
            value=8.0,
            key=f"discount_{scenario}"
        )
        # Margin of Safety
        mos = st.number_input(
            f"{scenario} Margin of Safety (%)",
            value=10.0 if scenario != "Worst" else 20.0,
            key=f"mos_{scenario}"
        )
        
        # KGV-relevant
        future_pe = st.number_input(
            f"{scenario} KGV am Ende (nur KGV-Modus)",
            value=15.0 + (5*(2 - i)),  # z.B. Best=25, Base=20, Worst=15
            key=f"pe_{scenario}"
        )
        
        # DCF-relevant
        fcf_margin = st.number_input(
            f"{scenario} FCF-Marge (%) (nur DCF)",
            value=10.0,
            key=f"fcf_{scenario}"
        )
        terminal_growth = st.number_input(
            f"{scenario} Terminal Growth (%) (nur DCF)",
            value=2.0,
            key=f"terminal_{scenario}"
        )

        scenario_data[scenario] = {
            "revenue_growth": revenue_growth,
            "net_margin": net_margin,
            "dilution": dilution,
            "discount_rate": discount,
            "margin_of_safety": mos,
            "future_pe": future_pe,
            "fcf_margin": fcf_margin,
            "terminal_growth": terminal_growth
        }

years = st.slider("Zeithorizont (Jahre):", 1, 15, 5)

###############################################################################
#  4) BERECHNUNG JE SZENARIO
###############################################################################
st.header("3) Ergebnisse")

# Hier speichern wir die Resultate + DataFrames pro Szenario
results = {}
dfs = {}

for scenario in scenario_names:
    sd = scenario_data[scenario]

    if valuation_method == "KGV-Ansatz":
        # KGV-Modell
        df_scen, fair_price, fair_price_mos = project_kgv_scenario(
            start_revenue=revenue_ttm,
            start_shares=shares_outstanding,
            start_net_margin=sd["net_margin"],
            annual_revenue_growth=sd["revenue_growth"],
            annual_dilution=sd["dilution"],
            future_pe=sd["future_pe"],
            discount_rate=sd["discount_rate"],
            margin_of_safety=sd["margin_of_safety"],
            years=years
        )
    else:
        # DCF-Modell
        df_scen, fair_price, fair_price_mos = project_dcf_scenario(
            start_revenue=revenue_ttm,
            start_shares=shares_outstanding,
            start_net_margin=sd["net_margin"],
            fcf_margin=sd["fcf_margin"],
            annual_revenue_growth=sd["revenue_growth"],
            annual_dilution=sd["dilution"],
            discount_rate=sd["discount_rate"],
            terminal_growth=sd["terminal_growth"],
            margin_of_safety=sd["margin_of_safety"],
            years=years
        )

    # Daten speichern
    results[scenario] = {
        "fair_no_mos": fair_price,
        "fair_with_mos": fair_price_mos
    }
    dfs[scenario] = df_scen

# Tabelle mit den Ergebnissen
res_table = []
for scenario in scenario_names:
    fair_no_mos = results[scenario]["fair_no_mos"]
    fair_with_mos = results[scenario]["fair_with_mos"]
    # Upside vs. aktueller Kurs
    if current_price > 0:
        upside = (fair_with_mos / current_price - 1) * 100
    else:
        upside = 0

    res_table.append([
        scenario,
        f"{fair_no_mos:.2f}",
        f"{fair_with_mos:.2f}",
        f"{upside:.2f} %"
    ])

df_results = pd.DataFrame(
    res_table,
    columns=["Szenario", "Fairer Preis (ohne MoS)", "Fairer Preis (mit MoS)", "Upside vs. Kurs"]
)
st.write(df_results)

st.write("""
- **Fairer Preis (ohne MoS)**: Diskontierter Wert ohne Sicherheitsabschlag  
- **Fairer Preis (mit MoS)**: Zusätzlich um die Margin of Safety reduziert  
- **Upside vs. Kurs**: Potenzielles Kurspotenzial gegenüber dem aktuellen Aktienkurs
""")

###############################################################################
#  5) GRAFISCHE DARSTELLUNG
###############################################################################
st.header("4) Grafische Darstellung")

st.write(f"**Bewertungsmethode**: {valuation_method}")

# Wir erstellen je nach Bewertungsmethode ein gemeinsames Diagramm
# - KGV: EPS-Verläufe pro Szenario
# - DCF: FCF-Verläufe pro Szenario

import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8,5))

if valuation_method == "KGV-Ansatz":
    # EPS-Entwicklung
    for scenario in scenario_names:
        df_scen = dfs[scenario]
        ax.plot(df_scen["Jahr"], df_scen["EPS"], marker='o', label=f"{scenario} EPS")
    ax.set_title("EPS-Entwicklung pro Szenario (KGV-Ansatz)")
    ax.set_ylabel("EPS (USD)")
else:
    # FCF-Entwicklung
    for scenario in scenario_names:
        df_scen = dfs[scenario]
        ax.plot(df_scen["Jahr"], df_scen["FCF"]/1e9, marker='o', label=f"{scenario} FCF (Mrd. USD)")
    ax.set_title("FCF-Entwicklung pro Szenario (DCF-Ansatz)")
    ax.set_ylabel("Free Cashflow (Mrd. USD)")

ax.set_xlabel("Jahr")
ax.grid(True)
ax.legend()
st.pyplot(fig)

st.success("Fertig! Alle gewünschten Punkte (Szenarien, MoS, KGV/DCF, Nettomargen, Diagramme) sind integriert.")
