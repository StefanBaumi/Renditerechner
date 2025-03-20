import streamlit as st
import pandas as pd

###############################################################################
# STREAMLIT-KONFIG
###############################################################################
st.set_page_config(page_title="Renditerechner (Lineare Annäherung)", layout="wide")

st.title("Renditerechner mit 3 Szenarien (Best, Base, Worst) – Lineare Annäherung")

st.markdown("""
Dieses Beispiel zeigt, wie man von **kurzfristigen** zu **langfristigen** Annahmen
über **10 Jahre** linear übergeht und daraus am Ende **7 Ergebniswerte** ableitet:
1) Umsatz  
2) Marktkapitalisierung  
3) Wertsteigerung  
4) Shareholder Yield  
5) Gesamtrendite  
6) Fairer Aktienkurs  
7) Margin of Safety  

**Hinweis**: Die Formeln sind vereinfacht. Passe sie an deine Bedürfnisse an.
""")

###############################################################################
# 1) STATUS QUO
###############################################################################
st.header("1) Status Quo")

col_sq1, col_sq2, col_sq3 = st.columns(3)

with col_sq1:
    current_revenue = st.number_input("Aktueller Umsatz (Mrd.)", value=500.0)
with col_sq2:
    current_marketcap = st.number_input("Aktuelle Marktkap. (Mrd.)", value=1000.0)
with col_sq3:
    current_shares = st.number_input("Aktienanzahl (Mrd. Stück)", value=10.0)

st.write("---")

###############################################################################
# 2) SZENARIEN-EINGABE: BEST, BASE, WORST
###############################################################################
st.header("2) Szenarien-Eingaben (kurz- und langfristig)")

scenario_names = ["Best", "Base", "Worst"]
scenario_data = {}

cols = st.columns(3)

def scenario_input(column, title, default_vals):
    """
    Helper, um pro Szenario (Kurz + Lang) die Inputs zu holen.
    default_vals: (growth_short, growth_long, margin_short, margin_long, kgv_short, kgv_long, yield_short, yield_long, mos)
    """
    with column:
        st.subheader(title)
        growth_short = st.number_input(f"{title} Wachstum kurzf. (%)", value=default_vals[0])
        growth_long = st.number_input(f"{title} Wachstum langfr. (%)", value=default_vals[1])
        margin_short = st.number_input(f"{title} Nettomarge kurzf. (%)", value=default_vals[2])
        margin_long = st.number_input(f"{title} Nettomarge langfr. (%)", value=default_vals[3])
        kgv_short = st.number_input(f"{title} KGV kurzf.", value=default_vals[4])
        kgv_long = st.number_input(f"{title} KGV langfr.", value=default_vals[5])
        shyield_short = st.number_input(f"{title} Shareholder Yield kurzf. (%)", value=default_vals[6])
        shyield_long = st.number_input(f"{title} Shareholder Yield langfr. (%)", value=default_vals[7])
        mos = st.number_input(f"{title} Margin of Safety (%)", value=default_vals[8])

    return {
        "growth_short": growth_short,
        "growth_long": growth_long,
        "margin_short": margin_short,
        "margin_long": margin_long,
        "kgv_short": kgv_short,
        "kgv_long": kgv_long,
        "shyield_short": shyield_short,
        "shyield_long": shyield_long,
        "mos": mos
    }

# Default-Werte nur als Beispiel
best_defaults = (15.0, 25.0, 10.0, 15.0, 20.0, 30.0, 2.0, 3.0, 10.0)
base_defaults = (10.0, 15.0, 8.0, 12.0, 15.0, 20.0, 1.0, 2.0, 15.0)
worst_defaults = (5.0, 10.0, 5.0, 8.0, 10.0, 15.0, 0.5, 1.0, 20.0)

scenario_data["Best"] = scenario_input(cols[0], "Best Case", best_defaults)
scenario_data["Base"] = scenario_input(cols[1], "Base Case", base_defaults)
scenario_data["Worst"] = scenario_input(cols[2], "Worst Case", worst_defaults)

st.write("---")

###############################################################################
# 3) BERECHNUNG
###############################################################################
st.header("3) Ergebnisse (nach 10 Jahren)")

years = 10  # wir nehmen an, nach 10 Jahren sind wir 'langfristig' angekommen

def linear_interpolate(start, end, t, total):
    """Lineare Interpolation von start nach end über total Zeiteinheiten."""
    return start + (end - start) * (t / total)

def calc_scenario(current_rev, current_mcap, current_shares, sc_data, years=10):
    """
    Führt die lineare Annäherung von kurz->lang durch:
    - revenue wächst jedes Jahr mit 'growth_t'
    - Nettomarge, KGV, Shareholder Yield interpolieren wir
    - am Ende (Jahr=10) berechnen wir:
        1) Umsatz
        2) Marktkapitalisierung
        3) Wertsteigerung
        4) Shareholder Yield
        5) Gesamtrendite
        6) Fairer Aktienkurs
        7) Margin of Safety
    """
    revenue = current_rev  # in Mrd.
    marketcap0 = current_mcap * 1e9  # in absoluten Zahlen
    shares_abs = current_shares * 1e9  # in absoluten Stück

    for t in range(1, years+1):
        # Wachstumsrate, Marge, KGV, Yield => linear interpoliert
        g_t = linear_interpolate(sc_data["growth_short"], sc_data["growth_long"], t, years)
        m_t = linear_interpolate(sc_data["margin_short"], sc_data["margin_long"], t, years)
        pe_t = linear_interpolate(sc_data["kgv_short"], sc_data["kgv_long"], t, years)
        shyield_t = linear_interpolate(sc_data["shyield_short"], sc_data["shyield_long"], t, years)

        # Umsatz(t)
        revenue *= (1 + g_t/100.0)

    # Jetzt haben wir revenue (in Jahr 10)
    final_revenue = revenue  # Mrd.

    # Nettomarge am Ende (t=10)
    final_margin = m_t
    # KGV am Ende (t=10)
    final_kgv = pe_t
    # Shareholder Yield am Ende (t=10)
    final_shyield = shyield_t

    # Gewinn in Jahr 10
    final_net_income = final_revenue * (final_margin / 100.0)  # Mrd.

    # MarketCap in Jahr 10
    final_mcap_abs = final_net_income * final_kgv * 1e9  # in absoluten Zahlen
    final_mcap_mrd = final_mcap_abs / 1e9  # wieder in Mrd.

    # Wertsteigerung = (MC(10) / MC(0)) - 1
    wertsteigerung = (final_mcap_abs / marketcap0) - 1

    # Gesamtrendite ~ wertsteigerung + shareyield (vereinfacht)
    gesamtrendite = (wertsteigerung * 100.0) + final_shyield

    # Fairer Aktienkurs (ohne MoS)
    fair_price = final_mcap_abs / shares_abs

    # Fairer Aktienkurs (mit MoS)
    mos_factor = 1 - sc_data["mos"] / 100.0
    fair_price_mos = fair_price * mos_factor

    # Ergebnis-Dict
    return {
        "Umsatz": final_revenue,                 # in Mrd.
        "Marktkapitalisierung": final_mcap_mrd,  # in Mrd.
        "Wertsteigerung": wertsteigerung * 100,  # in %
        "Shareholder Yield": final_shyield,      # in %
        "Gesamtrendite": gesamtrendite,          # in %
        "Fairer Aktienkurs": fair_price,         # in absoluten €
        "Margin of Safety": fair_price_mos       # in €
    }

results = {}
for scenario in scenario_names:
    sc_data = scenario_data[scenario]
    res = calc_scenario(current_revenue, current_marketcap, current_shares, sc_data, years)
    results[scenario] = res

###############################################################################
# 4) TABELLE MIT DEN 7 ERGEBNIS-WERTEN
###############################################################################
st.write("### Finale 7 Werte pro Szenario (nach 10 Jahren)")

rows = [
    "Umsatz (Mrd.)",
    "Marktkapitalisierung (Mrd.)",
    "Wertsteigerung (%)",
    "Shareholder Yield (%)",
    "Gesamtrendite (%)",
    "Fairer Aktienkurs (€)",
    "Fairer Aktienkurs (mit MoS) (€)"
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
*Alle Berechnungen sind stark vereinfacht und dienen nur als **Demo**, 
wie man von kurz- zu langfristigen Annahmen linear übergehen kann.*
""")
