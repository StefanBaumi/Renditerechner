import streamlit as st
import yfinance as yf
import pandas as pd

###############################################################################
# STREAMLIT-KONFIG
###############################################################################
st.set_page_config(
    page_title="Renditerechner (eine Ausschüttungsquote)",
    layout="wide"
)

st.title("Renditerechner mit 3 Szenarien – nur eine Ausschüttungsquote")

st.markdown("""
**Funktionen**:
1. Eingabe eines **Aktien-Tickers** → Laden von Basisdaten via `yfinance`.  
2. Drei Szenarien (Best, Base, Worst), jeweils mit **kurz- und langfristigen** Annahmen für Wachstum, Nettomarge und KGV.  
3. **Nur ein einziges Feld** für die Ausschüttungsquote (Payout Ratio), die für **alle** Szenarien verwendet wird.  
4. **Shareholder Yield** wird daraus berechnet (Ausschüttung / Marktkapitalisierung).  
5. **Margin of Safety** = (Fairer Kurs - Aktueller Kurs) / Fairer Kurs, als reiner Output.  
6. Lineare Annäherung (0–10 Jahre) von kurz- zu langfristigen Werten (Wachstum, Marge, KGV).
""")

###############################################################################
# 1) EINGABE: AKTIEN-TICKER + DATENLADEN
###############################################################################
st.header("1) Aktien-Ticker eingeben & Status Quo laden")

ticker = st.text_input("Aktien-Ticker (z.B. AAPL, AMZN, TSLA)", value="AAPL")

try:
    data = yf.Ticker(ticker).info
    current_price = data.get("regularMarketPrice", None)
    market_cap = data.get("marketCap", None)
    revenue_ttm = data.get("totalRevenue", None)
    shares_outstanding = data.get("sharesOutstanding", None)
except:
    data = {}
    current_price = None
    market_cap = None
    revenue_ttm = None
    shares_outstanding = None

# Fallback-Werte, falls yfinance nichts liefert
if current_price is None:
    current_price = 100.0
if market_cap is None:
    market_cap = 1.0e11
if revenue_ttm is None:
    revenue_ttm = 5.0e10
if (shares_outstanding is None) or (shares_outstanding == 0):
    shares_outstanding = market_cap / current_price

st.write(f"**Aktueller Kurs**: {current_price:.2f} USD")
st.write(f"**Marktkapitalisierung**: {market_cap/1e9:.2f} Mrd. USD")
st.write(f"**Umsatz (TTM)**: {revenue_ttm/1e9:.2f} Mrd. USD")
st.write(f"**Aktienanzahl**: {shares_outstanding/1e6:.2f} Mio. Stück")

# EIN FELD FÜR AUSSCHÜTTUNGSQUOTE
payout_ratio = st.number_input("Ausschüttungsquote (%)", value=10.0)

st.write("---")

###############################################################################
# 2) SZENARIEN-EINGABE (Best, Base, Worst) – NUR Wachstum, Marge, KGV
###############################################################################
st.header("2) Szenarien-Eingaben (kurz- und langfristig)")

scenario_names = ["Best", "Base", "Worst"]
scenario_data = {}
cols = st.columns(3)

def scenario_input(col, title, defaults):
    """
    defaults: (growth_short, growth_long, margin_short, margin_long, kgv_short, kgv_long)
    """
    with col:
        st.subheader(title)
        growth_short = st.number_input(f"{title} Wachstum kurzf. (%)", value=defaults[0])
        growth_long = st.number_input(f"{title} Wachstum langfr. (%)", value=defaults[1])
        margin_short = st.number_input(f"{title} Nettomarge kurzf. (%)", value=defaults[2])
        margin_long = st.number_input(f"{title} Nettomarge langfr. (%)", value=defaults[3])
        kgv_short = st.number_input(f"{title} KGV kurzf.", value=defaults[4])
        kgv_long = st.number_input(f"{title} KGV langfr.", value=defaults[5])

    return {
        "growth_short": growth_short,
        "growth_long": growth_long,
        "margin_short": margin_short,
        "margin_long": margin_long,
        "kgv_short": kgv_short,
        "kgv_long": kgv_long
    }

best_defaults = (15.0, 25.0, 10.0, 15.0, 20.0, 30.0)
base_defaults = (10.0, 15.0, 8.0, 12.0, 15.0, 20.0)
worst_defaults = (5.0, 10.0, 5.0, 8.0, 10.0, 15.0)

scenario_data["Best"] = scenario_input(cols[0], "Best Case", best_defaults)
scenario_data["Base"] = scenario_input(cols[1], "Base Case", base_defaults)
scenario_data["Worst"] = scenario_input(cols[2], "Worst Case", worst_defaults)

st.write("---")

###############################################################################
# 3) LINEARE INTERPOLATION & BERECHNUNG
###############################################################################
st.header("3) Ergebnisse (nach 10 Jahren)")

def linear_interpolate(start, end, t, total):
    """Lineare Interpolation von start -> end über total Zeiteinheiten."""
    return start + (end - start) * (t / total)

years = 10

def calc_scenario(cur_revenue, cur_mcap, cur_price, cur_shares, sc_data, payout, years=10):
    """
    1. Interpoliere Wachstum, Nettomarge, KGV von kurz->lang.
    2. Umsatz wächst pro Jahr mit 'growth_t'.
    3. Am Ende (Jahr 10) berechnen wir:
       - Gewinn = Umsatz * Nettomarge
       - Marktkapitalisierung = Gewinn * KGV
       - Ausschüttung = Gewinn * payout
       - Shareholder Yield = Ausschüttung / MarketCap
       - Gesamtrendite = Wertsteigerung + Shareholder Yield (vereinfacht)
       - Fairer Aktienkurs = Marktkapitalisierung / Aktienanzahl
       - Margin of Safety = (FairerKurs - AktuellerKurs)/FairerKurs
    """
    # Wir rechnen mit Mrd. für Umsatz
    revenue_mrd = cur_revenue / 1e9  # z.B. 5e10 => 50 Mrd
    marketcap_abs = cur_mcap  # z.B. 1e11
    shares_abs = cur_shares

    for t in range(1, years+1):
        g_t = linear_interpolate(sc_data["growth_short"], sc_data["growth_long"], t, years)
        m_t = linear_interpolate(sc_data["margin_short"], sc_data["margin_long"], t, years)
        pe_t = linear_interpolate(sc_data["kgv_short"], sc_data["kgv_long"], t, years)

        # Umsatz(t) in Mrd.
        revenue_mrd *= (1 + g_t/100.0)

    # Endwerte
    final_growth = g_t
    final_margin = m_t
    final_kgv = pe_t

    final_revenue_mrd = revenue_mrd
    final_net_income_mrd = final_revenue_mrd * (final_margin / 100.0)
    # MarketCap in absoluten Zahlen
    final_mcap_abs = final_net_income_mrd * final_kgv * 1e9
    final_mcap_mrd = final_mcap_abs / 1e9

    # Wertsteigerung
    wertsteigerung = (final_mcap_abs / marketcap_abs) - 1

    # Ausschüttung
    final_payout_amount_mrd = final_net_income_mrd * (payout / 100.0)
    if final_mcap_abs > 0:
        final_shyield = (final_payout_amount_mrd * 1e9 / final_mcap_abs) * 100.0
    else:
        final_shyield = 0.0

    # Gesamtrendite (vereinfacht)
    gesamtrendite = (wertsteigerung * 100.0) + final_shyield

    # Fairer Aktienkurs
    if shares_abs > 0:
        fair_price = final_mcap_abs / shares_abs
    else:
        fair_price = 0.0

    # Margin of Safety
    if fair_price > 0:
        mos = ((fair_price - cur_price) / fair_price) * 100.0
    else:
        mos = 0.0

    return {
        "Umsatz": final_revenue_mrd,
        "Marktkapitalisierung": final_mcap_mrd,
        "Wertsteigerung": wertsteigerung * 100.0,
        "Shareholder Yield": final_shyield,
        "Gesamtrendite": gesamtrendite,
        "Fairer Aktienkurs": fair_price,
        "Margin of Safety": mos
    }

results = {}
for scenario in scenario_names:
    sc_data = scenario_data[scenario]
    res = calc_scenario(
        cur_revenue=revenue_ttm,
        cur_mcap=market_cap,
        cur_price=current_price,
        cur_shares=shares_outstanding,
        sc_data=sc_data,
        payout=payout_ratio,
        years=years
    )
    results[scenario] = res

###############################################################################
# 4) TABELLE: 7 ERGEBNISWERTE
###############################################################################
st.write("### Finale 7 Werte pro Szenario (nach 10 Jahren)")

rows = [
    "Umsatz (Mrd.)",
    "Marktkapitalisierung (Mrd.)",
    "Wertsteigerung (%)",
    "Shareholder Yield (%)",
    "Gesamtrendite (%)",
    "Fairer Aktienkurs (USD)",
    "Margin of Safety (%)"
]

def format_res(res_dict):
    return [
        f"{res_dict['Umsatz']:.2f}",
        f"{res_dict['Marktkapitalisierung']:.2f}",
        f"{res_dict['Wertsteigerung']:.2f}",
        f"{res_dict['Shareholder Yield']:.2f}",
        f"{res_dict['Gesamtrendite']:.2f}",
        f"{res_dict['Fairer Aktienkurs']:.2f}",
        f"{res_dict['Margin of Safety']:.2f}"
    ]

table_data = {
    "Best": format_res(results["Best"]),
    "Base": format_res(results["Base"]),
    "Worst": format_res(results["Worst"])
}

df_output = pd.DataFrame(table_data, index=rows)
st.table(df_output)

st.markdown("""
**Hinweis**: Dieses Modell ist stark vereinfacht (keine Diskontierung, lineare 
Interpolation etc.). Du kannst es nach Belieben erweitern, z.B. um mehrstufige 
Wachstumsphasen, DCF-Berechnungen oder detailliertere Margen-Modelle.
""")
