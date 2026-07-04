"""
Génère bornes.db pour le dashboard Paris Bornes — 100% sources publiques.

Sources (aucune authentification requise) :
  - Belib' statique      : OpenData Ville de Paris (position, puissance, ~1900 bornes)
  - Belib' temps réel    : OpenData Ville de Paris (disponibilité)
Les tables d'analyse (pression, énergie, population, VE, projections) sont
reconstruites depuis les CSV d'étude du projet (dossier data/).

Usage : python build_data.py
"""
import io
import os
import re
import sqlite3

import pandas as pd
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "bornes.db")

OPENDATA = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets"
DS_STATIC = "belib-points-de-recharge-pour-vehicules-electriques-donnees-statiques"
DS_RT = "belib-points-de-recharge-pour-vehicules-electriques-disponibilite-temps-reel"


def _export_json(dataset):
    """Télécharge tous les enregistrements d'un dataset OpenData Paris."""
    url = f"{OPENDATA}/{dataset}/exports/json"
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def _num_arrondissement(row):
    """Déduit le numéro d'arrondissement (1-20) depuis l'INSEE ou l'adresse."""
    insee = str(row.get("code_insee_commune") or "")
    m = re.match(r"751(\d{2})", insee)
    if m:
        return int(m.group(1))
    adr = str(row.get("adresse_station") or "")
    m = re.search(r"750?(\d{2})\b", adr)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 20:
            return n
    return None


def construire_bornes():
    """Table `bornes` : une ligne par point de charge Belib', avec statut temps réel."""
    print("→ Téléchargement Belib' statique…")
    stat = _export_json(DS_STATIC)
    print(f"  {len(stat)} points de charge statiques")

    # coordonnées : coordonneesxy = {"lon":..., "lat":...}
    def _xy(v, k):
        if isinstance(v, dict):
            return v.get(k)
        return None

    stat["latitude"] = stat["coordonneesxy"].apply(lambda v: _xy(v, "lat"))
    stat["longitude"] = stat["coordonneesxy"].apply(lambda v: _xy(v, "lon"))
    stat["num_arrondissement"] = stat.apply(_num_arrondissement, axis=1)

    # statut temps réel (best-effort, non bloquant)
    statut_map = {}
    try:
        print("→ Téléchargement Belib' temps réel…")
        rt = _export_json(DS_RT)
        if "id_pdc" in rt.columns and "statut_pdc" in rt.columns:
            statut_map = dict(zip(rt["id_pdc"].astype(str), rt["statut_pdc"].astype(str)))
        print(f"  {len(rt)} statuts temps réel")
    except Exception as e:  # pragma: no cover
        print(f"  (temps réel indisponible, on garde le statut statique : {e})")

    def _statut(row):
        for key in ("id_pdc_itinerance", "id_pdc_local"):
            v = str(row.get(key) or "")
            if v in statut_map:
                return statut_map[v]
        return row.get("statut_pdc") or "Inconnu"

    stat["statut_actuel"] = stat.apply(_statut, axis=1)

    cols = {
        "id_pdc_itinerance": "id_pdc_itinerance",
        "id_station_itinerance": "id_station_itinerance",
        "nom_station": "nom_station",
        "nom_amenageur": "nom_amenageur",
        "nom_operateur": "nom_operateur",
        "puissance_nominale": "puissance_nominale",
        "latitude": "latitude",
        "longitude": "longitude",
        "code_insee_commune": "code_insee_commune",
        "date_mise_en_service": "date_mise_en_service",
        "num_arrondissement": "num_arrondissement",
        "statut_actuel": "statut_actuel",
    }
    df = pd.DataFrame({dst: stat.get(src) for src, dst in cols.items()})
    df["source"] = "belib"
    df = df.dropna(subset=["num_arrondissement", "latitude", "longitude"])
    df["num_arrondissement"] = df["num_arrondissement"].astype(int)
    return df


def _csv(name):
    return pd.read_csv(os.path.join(DATA_DIR, name))


def construire_tables_analyse():
    """Tables pression / population / vehicules_electriques / energie depuis les CSV d'étude."""
    energie = _csv("energie_by_arrdt.csv")      # arr_num × scenario × horizon
    pstar = _csv("p_star_ajuste.csv")           # 1 ligne / arrondissement

    # snapshot "actuel" = une ligne par arrondissement (indépendant du scénario)
    actuel = (
        energie.sort_values(["arr_num", "horizon_years"])
        .groupby("arr_num", as_index=False)
        .first()
    )

    population = pd.DataFrame({
        "num_arrondissement": actuel["arr_num"].astype(int),
        "codgeo": actuel["arr_num"].apply(lambda a: f"751{int(a):02d}"),
        "pop_total": actuel["population"].astype(int),
        "pop_majeurs_18plus": None,
        "pop_mineurs_0_17": None,
        "pct_majeurs": None,
    })

    vehicules = pd.DataFrame({
        "num_arrondissement": actuel["arr_num"].astype(int),
        "date_arrete": "2026",
        "nb_ve": actuel["nb_ve"].astype(int),
        "nb_vp_total": None,
        "taux_ve": None,
    })

    pression = pd.DataFrame({
        "num_arrondissement": actuel["arr_num"].astype(int),
        "nb_ve": actuel["nb_ve"].astype(int),
        "nb_vp_total": None,
        "nb_pdc": actuel["nb_bornes"].astype(int),
        "pression": actuel["pression_actuelle"].astype(float),
        "taux_ve": None,
        "taux_disponibilite": None,
    })

    energie_tbl = pd.DataFrame({
        "num_arrondissement": actuel["arr_num"].astype(int),
        "code_commune": actuel["arr_num"].apply(lambda a: f"751{int(a):02d}"),
        "nom_commune": actuel["arr_num"].apply(lambda a: f"Paris {int(a)}e"),
        "code_grand_secteur": "Résidentiel",
        "conso_totale_mwh": actuel["conso_mwh"].astype(float),
        "nb_sites": None,
        "num_arrondissement2": actuel["arr_num"].astype(int),
    }).drop(columns=["num_arrondissement2"])

    return pression, population, vehicules, energie_tbl


def main():
    bornes = construire_bornes()
    pression, population, vehicules, energie = construire_tables_analyse()

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    bornes.to_sql("bornes", con, index=False, if_exists="replace")
    pression.to_sql("pression", con, index=False, if_exists="replace")
    population.to_sql("population", con, index=False, if_exists="replace")
    vehicules.to_sql("vehicules_electriques", con, index=False, if_exists="replace")
    energie.to_sql("energie", con, index=False, if_exists="replace")
    con.close()

    print("\n✓ bornes.db généré")
    print(f"  bornes                : {len(bornes):>5} points de charge")
    print(f"  pression              : {len(pression):>5} arrondissements")
    print(f"  population            : {len(population):>5} arrondissements")
    print(f"  vehicules_electriques : {len(vehicules):>5} arrondissements")
    print(f"  energie               : {len(energie):>5} arrondissements")


if __name__ == "__main__":
    main()
