"""
Calculele pentru tab-ul de "Indicatori avansați" (bazat pe Supabase).

Ținut separat de app.py, ca fiecare funcție să facă un singur calcul clar
și să fie ușor de testat/modificat fără să atingi restul aplicației.
"""

import pandas as pd


def gaseste_luna_curenta(df):
    """'Luna curentă' = cea mai recentă lună pentru care există date în 2026.
    Nu folosim data calendaristică de azi, pentru că datele pot fi introduse
    cu întârziere (ex: suntem în iulie, dar ultimele date complete sunt mai)."""
    df_2026 = df[df["year_data"] == 2026]
    if df_2026.empty:
        return None
    return int(df_2026["month_num"].max())


def suma_pe_perioada(df, year, luni):
    """Suma Vz Val și GM pentru un an și o listă de luni (month_num)."""
    subset = df[(df["year_data"] == year) & (df["month_num"].isin(luni))]
    return {
        "vz_val": float(subset["vz_val"].sum()),
        "gm": float(subset["gm"].sum()),
    }


def calculeaza_indicatori(df, df_curs):
    """Returnează un dicționar cu toți indicatorii ceruți, gata de afișat."""

    luna_curenta = gaseste_luna_curenta(df)
    if luna_curenta is None:
        return None

    # --- MTD (luna curentă) 2026 vs aceeași lună 2025 ---
    mtd_2026 = suma_pe_perioada(df, 2026, [luna_curenta])
    mtd_2025 = suma_pe_perioada(df, 2025, [luna_curenta])

    # --- Last Year = anul 2025 întreg ---
    ly_total = suma_pe_perioada(df, 2025, list(range(1, 13)))

    # --- YTD: toate lunile de la 1 până la luna curentă, în ambii ani ---
    luni_ytd = list(range(1, luna_curenta + 1))
    ytd_2026 = suma_pe_perioada(df, 2026, luni_ytd)
    ytd_2025 = suma_pe_perioada(df, 2025, luni_ytd)

    def variatie_procentuala(nou, vechi):
        if not vechi:
            return None
        return (nou - vechi) / abs(vechi) * 100

    def marja_procentuala(gm, vz_val):
        if not vz_val:
            return None
        return gm / vz_val * 100

    gm_pct_mtd_2026 = marja_procentuala(mtd_2026["gm"], mtd_2026["vz_val"])
    gm_pct_mtd_2025 = marja_procentuala(mtd_2025["gm"], mtd_2025["vz_val"])

    # --- Conversie EUR pe lună: Vz Val (RON) / curs mediu lunar ---
    curs_dict = {
        (int(r["year_data"]), int(r["month_num"])): float(r["curs_eur_ron"])
        for _, r in df_curs.iterrows()
    }

    df_luni = (
        df.groupby(["year_data", "month_num"], as_index=False)["vz_val"]
        .sum()
        .sort_values(["year_data", "month_num"])
    )
    df_luni["curs_eur_ron"] = df_luni.apply(
        lambda r: curs_dict.get((int(r["year_data"]), int(r["month_num"]))), axis=1
    )
    df_luni["vz_val_eur"] = df_luni["vz_val"] / df_luni["curs_eur_ron"]

    return {
        "luna_curenta_num": luna_curenta,
        "mtd_2026": mtd_2026,
        "mtd_2025": mtd_2025,
        "ly_total": ly_total,
        "ytd_2026": ytd_2026,
        "ytd_2025": ytd_2025,
        "vz_val_variatie_mtd": variatie_procentuala(mtd_2026["vz_val"], mtd_2025["vz_val"]),
        "vz_val_variatie_ytd": variatie_procentuala(ytd_2026["vz_val"], ytd_2025["vz_val"]),
        "gm_variatie_mtd": variatie_procentuala(mtd_2026["gm"], mtd_2025["gm"]),
        "gm_variatie_ytd": variatie_procentuala(ytd_2026["gm"], ytd_2025["gm"]),
        "gm_pct_mtd_2026": gm_pct_mtd_2026,
        "gm_pct_mtd_2025": gm_pct_mtd_2025,
        "gm_pct_variatie_mtd": (
            None if gm_pct_mtd_2026 is None or gm_pct_mtd_2025 is None
            else gm_pct_mtd_2026 - gm_pct_mtd_2025
        ),
        "conversie_eur_pe_luna": df_luni,
    }


def vanzari_pe_locatie(df):
    """Vânzări totale grupate pe locație (district + numele punctului de livrare)."""
    return (
        df.groupby(["district", "delivery_name"], as_index=False)
        .agg(vz_val=("vz_val", "sum"), gm=("gm", "sum"), vz_q=("vz_q", "sum"))
        .sort_values("vz_val", ascending=False)
    )
