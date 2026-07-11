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

            st.plotly_chart(fig_map, use_container_width=True)

            if not nepotrivite.empty:
                with st.expander("Județe care nu au putut fi potrivite pe hartă"):
                    st.dataframe(nepotrivite, use_container_width=True)

        except Exception as e:
            st.warning(f"Harta nu a putut fi încărcată: {e}")
            st.dataframe(sales_by_district, use_container_width=True)
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
            st.plotly_chart(fig_brand_donut, use_container_width=True)
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
            st.plotly_chart(fig_channel_donut, use_container_width=True)
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
            st.dataframe(top_clients, use_container_width=True)
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
            st.dataframe(top_products, use_container_width=True)
        else:
            st.info("Lipsesc coloanele necesare pentru acest tabel.")

    # ---------------------------------------------------
    # DATE FILTRATE
    # ---------------------------------------------------
    st.subheader("Date filtrate")
    st.dataframe(filtered_df, use_container_width=True)

else:
    st.info("Încarcă fișiere Excel pentru a vedea dashboard-ul.")
