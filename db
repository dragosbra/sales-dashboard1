"""
Modul separat pentru tot ce ține de baza de date (Supabase).

Îl ținem separat de app.py ca să fie clar ce e "dashboard" (citește Excel,
afișează grafice pe loc, per sesiune) și ce e "bază de date" (salvare
permanentă, indicatori care compară ani/luni diferite).
"""

import pandas as pd
import streamlit as st
from supabase import create_client

LUNI_RO_EN = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}
NUME_LUNA = {v: k for k, v in LUNI_RO_EN.items()}


@st.cache_resource
def get_client():
    """Creează conexiunea la Supabase, o singură dată per sesiune de server.
    Cheile vin din st.secrets (fișierul secrets.toml local, sau Secrets din
    Streamlit Community Cloud, niciodată scrise direct în cod)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def fisier_deja_incarcat(nume_fisier):
    """Verifică în baza de date dacă acest fișier a mai fost încărcat vreodată,
    ca să nu dublăm datele dacă cineva încarcă din greșeală același Excel de
    două ori (inclusiv în sesiuni/zile diferite - nu doar în sesiunea curentă)."""
    client = get_client()
    rezultat = (
        client.table("vanzari")
        .select("id", count="exact")
        .eq("sursa_fisier", nume_fisier)
        .limit(1)
        .execute()
    )
    return (rezultat.count or 0) > 0


def salveaza_dataframe(df, nume_fisier):
    """Trimite rândurile unui DataFrame (deja citit dintr-un Excel) în tabela
    'vanzari' din Supabase. Presupune coloanele standard din fișierele tale."""
    client = get_client()

    randuri = []
    for _, r in df.iterrows():
        luna_text = str(r.get("Month of Data", "")).strip()
        randuri.append({
            "year_data": int(r.get("Year of Data")),
            "month_data": luna_text,
            "month_num": LUNI_RO_EN.get(luna_text, 0),
            "salesman": str(r.get("Salesman", "")),
            "partner_clasificare": str(r.get("Partner Clasificare", "")),
            "partner_name": str(r.get("Partner Name", "")),
            "item_code": str(r.get("Item – ItemCode", "")),
            "item_articol": str(r.get("Item - Articol", "")),
            "item_brand": str(r.get("Item - Brand", "")),
            "district": str(r.get("DeliveryAddress - District", "")),
            "delivery_name": str(r.get("DeliveryAddress - Name", "")),
            "vz_val": float(r.get("Vz Val", 0) or 0),
            "gm": float(r.get("GM", 0) or 0),
            "vz_discount": float(r.get("VzDiscount", 0) or 0),
            "vz_q": float(r.get("Vz Q", 0) or 0),
            "sursa_fisier": nume_fisier,
        })

    # Inserăm în loturi de 500, ca să nu depășim limitele unui singur request
    for i in range(0, len(randuri), 500):
        client.table("vanzari").insert(randuri[i:i + 500]).execute()


@st.cache_data(ttl=300)
def incarca_toate_vanzarile():
    """Citește TOATĂ istoria de vânzări din Supabase (nu doar sesiunea curentă).
    Cache 5 minute, ca să nu batem baza de date la fiecare interacțiune."""
    client = get_client()

    toate = []
    inceput = 0
    pas = 1000
    while True:
        rezultat = (
            client.table("vanzari")
            .select("*")
            .range(inceput, inceput + pas - 1)
            .execute()
        )
        date = rezultat.data
        if not date:
            break
        toate.extend(date)
        if len(date) < pas:
            break
        inceput += pas

    if not toate:
        return pd.DataFrame()

    return pd.DataFrame(toate)


@st.cache_data(ttl=3600)
def incarca_curs_valutar():
    """Citește tabela cu cursul mediu lunar EUR/RON."""
    client = get_client()
    rezultat = client.table("curs_valutar").select("*").execute()
    return pd.DataFrame(rezultat.data)