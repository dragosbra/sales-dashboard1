import json
import unicodedata

import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------
# SETĂRI PAGINĂ
# ---------------------------------------------------
st.set_page_config(
    page_title="Sales Dashboard",
    layout="wide"
)



def pagina_dashboard_sesiune():
    """Dashboard-ul original: citește Excel-uri în sesiunea curentă (nu se salvează permanent)."""
    st.title("Sales Dashboard")
    st.write("Încarcă unul sau mai multe fișiere Excel pentru analiză.")

    # ---------------------------------------------------
    # MEMORIE SESIUNE
    # ---------------------------------------------------
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = {}

    # ---------------------------------------------------
    # UPLOAD FIȘIERE
    # ---------------------------------------------------
    uploaded_files = st.file_uploader(
        "Alege fișiere Excel",
        type=["xlsx", "xls"],
        accept_multiple_files=True
    )

    # ---------------------------------------------------
    # CITIRE FIȘIERE
    # ---------------------------------------------------
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name

            if file_name in st.session_state.uploaded_data:
                st.warning(f"Fișierul '{file_name}' este deja încărcat.")
            else:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.session_state.uploaded_data[file_name] = df
                    st.success(f"Fișierul '{file_name}' a fost încărcat cu succes.")
                except Exception as e:
                    st.error(f"Eroare la citirea fișierului '{file_name}': {e}")

    # ---------------------------------------------------
    # DACĂ EXISTĂ DATE ÎNCĂRCATE, AFIȘĂM DASHBOARD-UL
    # ---------------------------------------------------
    if st.session_state.uploaded_data:

        st.subheader("Fișiere încărcate în sesiunea curentă")
        for file_name in st.session_state.uploaded_data.keys():
            st.write(f"- {file_name}")

        # ---------------------------------------------------
        # COMBINĂM TOATE FIȘIERELE
        # ---------------------------------------------------
        combined_df = pd.concat(
            st.session_state.uploaded_data.values(),
            ignore_index=True
        )

        # ---------------------------------------------------
        # CONVERTIM COLOANELE NUMERICE
        # ---------------------------------------------------
        numeric_columns = ["Vz Val", "GM", "VzDiscount", "Vz Q"]

        for col in numeric_columns:
            if col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce")

        # ---------------------------------------------------
        # NORMALIZĂM COLOANELE DE TEXT
        # ---------------------------------------------------
        # Unele coloane (ex: coduri de produs) pot avea în Excel un amestec de
        # numere și text (ex: "12345" și "DISCOUNT_CASH_11" în aceeași coloană).
        # Streamlit încearcă să convertească automat tabelul la un format optim
        # (Arrow) și crapă dacă găsește tipuri amestecate. Transformăm toate
        # coloanele care NU sunt numerice în text simplu, ca să evităm eroarea.
        for col in combined_df.columns:
            if col not in numeric_columns:
                combined_df[col] = combined_df[col].astype(str).replace("nan", "")

        # ---------------------------------------------------
        # FILTRE
        # ---------------------------------------------------
        st.subheader("Filtre")

        col_filter_1, col_filter_2, col_filter_3 = st.columns(3)

        with col_filter_1:
            salesman_options = ["Toți"] + sorted(
                combined_df["Salesman"].dropna().astype(str).unique().tolist()
            ) if "Salesman" in combined_df.columns else ["Toți"]
            selected_salesman = st.selectbox("Alege agentul de vânzări", salesman_options)

        with col_filter_2:
            brand_options = ["Toate"] + sorted(
                combined_df["Item - Brand"].dropna().astype(str).unique().tolist()
            ) if "Item - Brand" in combined_df.columns else ["Toate"]
            selected_brand = st.selectbox("Alege brandul", brand_options)

        with col_filter_3:
            month_options = ["Toate"] + sorted(
                combined_df["Month of Data"].dropna().astype(str).unique().tolist()
            ) if "Month of Data" in combined_df.columns else ["Toate"]
            selected_month = st.selectbox("Alege luna", month_options)

        # ---------------------------------------------------
        # APLICĂM FILTRELE
        # ---------------------------------------------------
        filtered_df = combined_df.copy()

        if selected_salesman != "Toți" and "Salesman" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Salesman"].astype(str) == selected_salesman]

        if selected_brand != "Toate" and "Item - Brand" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Item - Brand"].astype(str) == selected_brand]

        if selected_month != "Toate" and "Month of Data" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Month of Data"].astype(str) == selected_month]

        # ---------------------------------------------------
        # KPI-URI
        # ---------------------------------------------------
        st.subheader("Indicatori principali")

        total_sales = filtered_df["Vz Val"].sum() if "Vz Val" in filtered_df.columns else 0
        total_gm = filtered_df["GM"].sum() if "GM" in filtered_df.columns else 0
        total_discount = filtered_df["VzDiscount"].sum() if "VzDiscount" in filtered_df.columns else 0
        total_quantity = filtered_df["Vz Q"].sum() if "Vz Q" in filtered_df.columns else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        kpi1.metric("Cifră de afaceri", f"{total_sales:,.2f} RON")
        kpi2.metric("Marjă brută", f"{total_gm:,.2f} RON")
        kpi3.metric("Discount total", f"{total_discount:,.2f} RON")
        kpi4.metric("Cantitate vândută", f"{total_quantity:,.0f}")

        # ---------------------------------------------------
        # HARTĂ VÂNZĂRI PE JUDEȚE
        # ---------------------------------------------------
        st.subheader("Hartă vânzări pe județe")

        def normalizeaza(text):
            """Elimină diacriticele și spațiile în plus, pentru a putea potrivi
            denumirile de județe indiferent cum sunt scrise (cu/fără diacritice)."""
            text = str(text).strip()
            text = unicodedata.normalize("NFKD", text)
            text = "".join(ch for ch in text if not unicodedata.combining(ch))
            return text.lower()

        if "DeliveryAddress - District" in filtered_df.columns and "Vz Val" in filtered_df.columns:

            sales_by_district = filtered_df.groupby(
                "DeliveryAddress - District", as_index=False
            )["Vz Val"].sum()

            try:
                with open("romania-counties.geojson", "r", encoding="utf-8") as f:
                    romania_geojson = json.load(f)

                # construim un dicționar: nume normalizat -> numele exact din geojson
                geojson_names = {
                    normalizeaza(feat["properties"]["NAME_1"]): feat["properties"]["NAME_1"]
                    for feat in romania_geojson["features"]
                }

                # câteva corespondențe suplimentare pentru variații uzuale de scriere
                alias_manual = {
                    "bucuresti": "Bucuresti",
                    "municipiul bucuresti": "Bucuresti",
                    "mun. bucuresti": "Bucuresti",
                    "sector 1": "Bucuresti",
                    "sector 2": "Bucuresti",
                    "sector 3": "Bucuresti",
                    "sector 4": "Bucuresti",
                    "sector 5": "Bucuresti",
                    "sector 6": "Bucuresti",
                    "cluj napoca": "Cluj",
                    "cluj-napoca": "Cluj",
                    "nespec": None,
                    "<nespec>": None,
                    "": None,
                    "nan": None,
                }

                def mapeaza_judet(nume_district):
                    cheie = normalizeaza(nume_district)
                    if cheie in alias_manual:
                        return alias_manual[cheie]
                    return geojson_names.get(cheie)

                sales_by_district["district_map"] = sales_by_district[
                    "DeliveryAddress - District"
                ].apply(mapeaza_judet)

                nepotrivite = sales_by_district[sales_by_district["district_map"].isna()]
                sales_by_district = sales_by_district[sales_by_district["district_map"].notna()]

                fig_map = px.choropleth(
                    sales_by_district,
                    geojson=romania_geojson,
                    locations="district_map",
                    featureidkey="properties.NAME_1",
                    color="Vz Val",
                    color_continuous_scale="Blues",
                    projection="mercator",
                    hover_name="district_map",
                    hover_data={"Vz Val": ":,.0f"}
                )

                fig_map.update_geos(fitbounds="locations", visible=False)
                fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=550)

                st.plotly_chart(fig_map, width='stretch')

                if not nepotrivite.empty:
                    with st.expander("Județe care nu au putut fi potrivite pe hartă"):
                        st.dataframe(nepotrivite, width='stretch')

            except Exception as e:
                st.warning(f"Harta nu a putut fi încărcată: {e}")
                st.dataframe(sales_by_district, width='stretch')
        else:
            st.info(
                "Pentru a afișa harta este nevoie de coloanele "
                "'DeliveryAddress - District' și 'Vz Val' în fișierele încărcate."
            )

        # ---------------------------------------------------
        # GRAFICE
        # ---------------------------------------------------
        chart_col_1, chart_col_2 = st.columns(2)

        with chart_col_1:
            st.subheader("Vânzări pe brand")
            if "Item - Brand" in filtered_df.columns and "Vz Val" in filtered_df.columns:
                sales_by_brand = (
                    filtered_df.groupby("Item - Brand")["Vz Val"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                )
                st.bar_chart(sales_by_brand)
            else:
                st.info("Lipsesc coloanele necesare pentru acest grafic.")

        with chart_col_2:
            st.subheader("Vânzări pe agenți")
            if "Salesman" in filtered_df.columns and "Vz Val" in filtered_df.columns:
                sales_by_salesman = (
                    filtered_df.groupby("Salesman")["Vz Val"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                )
                st.bar_chart(sales_by_salesman)
            else:
                st.info("Lipsesc coloanele necesare pentru acest grafic.")

        # ---------------------------------------------------
        # DONUT CHART - PONDERE VÂNZĂRI PE BRAND
        # ---------------------------------------------------
        donut_col_1, donut_col_2 = st.columns(2)

        with donut_col_1:
            st.subheader("Pondere vânzări pe brand")
            if "Item - Brand" in filtered_df.columns and "Vz Val" in filtered_df.columns:
                sales_by_brand_donut = (
                    filtered_df.groupby("Item - Brand", as_index=False)["Vz Val"]
                    .sum()
                    .sort_values("Vz Val", ascending=False)
                    .head(8)
                )

                fig_brand_donut = px.pie(
                    sales_by_brand_donut,
                    names="Item - Brand",
                    values="Vz Val",
                    hole=0.5,
                )
                fig_brand_donut.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_brand_donut, width='stretch')
            else:
                st.info("Lipsesc coloanele necesare pentru acest grafic.")

        with donut_col_2:
            st.subheader("Pondere vânzări pe canal")
            if "Canal" in filtered_df.columns and "Vz Val" in filtered_df.columns:
                sales_by_channel_donut = (
                    filtered_df.groupby("Canal", as_index=False)["Vz Val"]
                    .sum()
                    .sort_values("Vz Val", ascending=False)
                    .head(8)
                )

                fig_channel_donut = px.pie(
                    sales_by_channel_donut,
                    names="Canal",
                    values="Vz Val",
                    hole=0.5,
                )
                fig_channel_donut.update_traces(textinfo="percent+label")
                st.plotly_chart(fig_channel_donut, width='stretch')
            else:
                st.info("Lipsesc coloanele necesare pentru acest grafic.")

        # ---------------------------------------------------
        # TABELE
        # ---------------------------------------------------
        table_col_1, table_col_2 = st.columns(2)

        with table_col_1:
            st.subheader("Top 10 clienți")
            if "Partner Name" in filtered_df.columns and "Vz Val" in filtered_df.columns:
                top_clients = (
                    filtered_df.groupby("Partner Name", as_index=False)["Vz Val"]
                    .sum()
                    .sort_values("Vz Val", ascending=False)
                    .head(10)
                )
                st.dataframe(top_clients, width='stretch')
            else:
                st.info("Lipsesc coloanele necesare pentru acest tabel.")

        with table_col_2:
            st.subheader("Top 5 produse")
            if "Item - Articol" in filtered_df.columns and "Vz Val" in filtered_df.columns:
                top_products = (
                    filtered_df.groupby("Item - Articol", as_index=False)["Vz Val"]
                    .sum()
                    .sort_values("Vz Val", ascending=False)
                    .head(5)
                )
                st.dataframe(top_products, width='stretch')
            else:
                st.info("Lipsesc coloanele necesare pentru acest tabel.")

        # ---------------------------------------------------
        # DATE FILTRATE
        # ---------------------------------------------------
        st.subheader("Date filtrate")
        st.dataframe(filtered_df, width='stretch')

    else:
        st.info("Încarcă fișiere Excel pentru a vedea dashboard-ul.")


# ============================================================
# PAGINA 2: INDICATORI AVANSAȚI (bază de date permanentă, Supabase)
# ============================================================
def pagina_indicatori_avansati():
    """Indicatori care compară 2026 vs 2025, calculați din TOATE datele
    salvate vreodată în baza de date - nu doar din fișierele încărcate în
    sesiunea curentă. De-asta e complet separată de dashboard-ul de mai sus."""

    import db
    import kpi_avansati

    st.header("Indicatori avansați (bază de date)")
    st.caption(
        "Aceste date sunt salvate permanent într-o bază de date. Odată ce "
        "încarci un fișier aici, el rămâne disponibil oricând revii, pe orice "
        "calculator."
    )

    # ---------------------------------------------------
    # VERIFICARE CONFIGURARE SUPABASE
    # ---------------------------------------------------
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        st.error(
            "Baza de date nu este configurată încă. Adaugă SUPABASE_URL și "
            "SUPABASE_KEY în Secrets (vezi SETUP_SUPABASE.md)."
        )
        return

    # ---------------------------------------------------
    # UPLOAD FIȘIERE -> SALVARE PERMANENTĂ ÎN SUPABASE
    # ---------------------------------------------------
    fisiere_noi = st.file_uploader(
        "Încarcă fișiere Excel (se salvează permanent în baza de date)",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key="uploader_db",
    )

    if fisiere_noi:
        for fisier in fisiere_noi:
            if db.fisier_deja_incarcat(fisier.name):
                st.warning(f"Fișierul '{fisier.name}' a fost deja încărcat anterior în baza de date.")
                continue
            try:
                df_nou = pd.read_excel(fisier)
                with st.spinner(f"Salvez '{fisier.name}' în baza de date..."):
                    db.salveaza_dataframe(df_nou, fisier.name)
                st.success(f"'{fisier.name}' a fost salvat permanent.")
                db.incarca_toate_vanzarile.clear()
            except Exception as e:
                st.error(f"Eroare la '{fisier.name}': {e}")

    # ---------------------------------------------------
    # CITIM TOT ISTORICUL DIN BAZA DE DATE
    # ---------------------------------------------------
    df = db.incarca_toate_vanzarile()

    if df.empty:
        st.info("Nu există încă date în baza de date. Încarcă un fișier Excel mai sus.")
        return

    df_curs = db.incarca_curs_valutar()
    indicatori = kpi_avansati.calculeaza_indicatori(df, df_curs)

    if indicatori is None:
        st.info("Nu există date pentru anul 2026 încă, deci nu putem calcula 'luna curentă'.")
        return

    luna_num = indicatori["luna_curenta_num"]
    nume_luna = db.NUME_LUNA.get(luna_num, str(luna_num))

    st.subheader(f"Luna curentă (MTD): {nume_luna}")

    def afiseaza_delta(valoare):
        return None if valoare is None else f"{valoare:+.1f}%"

    # --- Vânzări ---
    st.markdown("#### Vânzări")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"{nume_luna} 2026", f"{indicatori['mtd_2026']['vz_val']:,.0f} RON")
    c2.metric(f"{nume_luna} 2025", f"{indicatori['mtd_2025']['vz_val']:,.0f} RON",
               delta=afiseaza_delta(indicatori["vz_val_variatie_mtd"]))
    c3.metric("Total 2025 (Last Year)", f"{indicatori['ly_total']['vz_val']:,.0f} RON")
    c4.metric("YTD 2026 vs YTD 2025", f"{indicatori['ytd_2026']['vz_val']:,.0f} RON",
               delta=afiseaza_delta(indicatori["vz_val_variatie_ytd"]))

    # --- Marjă brută ---
    st.markdown("#### Marjă brută (GM)")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric(f"GM {nume_luna} 2026", f"{indicatori['mtd_2026']['gm']:,.0f} RON")
    g2.metric(f"GM {nume_luna} 2025", f"{indicatori['mtd_2025']['gm']:,.0f} RON",
               delta=afiseaza_delta(indicatori["gm_variatie_mtd"]))
    g3.metric("GM Total 2025 (Last Year)", f"{indicatori['ly_total']['gm']:,.0f} RON")
    g4.metric("GM YTD 2026 vs YTD 2025", f"{indicatori['ytd_2026']['gm']:,.0f} RON",
               delta=afiseaza_delta(indicatori["gm_variatie_ytd"]))

    # --- Marjă procentuală ---
    st.markdown("#### Marjă procentuală (GM / Vânzări)")
    p1, p2, p3 = st.columns(3)
    gm_pct_2026 = indicatori["gm_pct_mtd_2026"]
    gm_pct_2025 = indicatori["gm_pct_mtd_2025"]
    p1.metric(f"Marjă % {nume_luna} 2026", f"{gm_pct_2026:.1f}%" if gm_pct_2026 is not None else "—")
    p2.metric(f"Marjă % {nume_luna} 2025", f"{gm_pct_2025:.1f}%" if gm_pct_2025 is not None else "—")
    diferenta = indicatori["gm_pct_variatie_mtd"]
    p3.metric("Diferență MTD vs LY (puncte procentuale)",
               f"{diferenta:+.1f} pp" if diferenta is not None else "—")

    # --- Conversie EUR pe lună ---
    st.markdown("#### Vânzări convertite în EUR, pe lună")
    st.caption(
        "Conversia folosește cursul mediu lunar oficial BNR pentru fiecare "
        "lună (nu un curs unic pe an) - vezi/actualizează valorile în tabela "
        "'curs_valutar' din Supabase."
    )
    df_eur = indicatori["conversie_eur_pe_luna"].copy()
    df_eur["luna"] = df_eur.apply(
        lambda r: f"{db.NUME_LUNA.get(int(r['month_num']), '')} {int(r['year_data'])}", axis=1
    )
    fig_eur = px.bar(
        df_eur, x="luna", y="vz_val_eur",
        labels={"vz_val_eur": "Vânzări (EUR)", "luna": "Lună"},
    )
    st.plotly_chart(fig_eur, width="stretch")
    st.dataframe(
        df_eur[["luna", "vz_val", "curs_eur_ron", "vz_val_eur"]].rename(columns={
            "vz_val": "Vânzări (RON)", "curs_eur_ron": "Curs mediu EUR/RON", "vz_val_eur": "Vânzări (EUR)"
        }),
        width="stretch",
    )

    # --- Vânzări pe locație ---
    st.markdown("#### Vânzări pe locație")
    df_locatii = kpi_avansati.vanzari_pe_locatie(df)
    st.dataframe(
        df_locatii.rename(columns={
            "district": "Județ", "delivery_name": "Locație livrare",
            "vz_val": "Vânzări (RON)", "gm": "Marjă brută (RON)", "vz_q": "Cantitate",
        }),
        width="stretch",
    )


# ============================================================
# NAVIGARE ÎNTRE CELE DOUĂ PAGINI
# ============================================================
pagina = st.sidebar.radio(
    "Navigare",
    ["Dashboard (sesiune curentă)", "Indicatori avansați (bază de date)"],
)

if pagina == "Dashboard (sesiune curentă)":
    pagina_dashboard_sesiune()
else:
    pagina_indicatori_avansati()
