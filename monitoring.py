"""
Monitoring léger intégré au dashboard Paris Bornes.

Objectif : répondre à l'exigence "show your results in a monitoring tool" sans
introduire de dépendance lourde (MLflow / Grafana). On suit trois familles
d'indicateurs, directement dans l'application :

  1. Fraîcheur & qualité des données  (données publiques → base SQLite)
  2. Résultats du modèle de projection (15 combinaisons scénario × horizon)
  3. Usage de l'application            (journal de visites best-effort)

Tout est stocké dans la base SQLite `bornes.db` déjà utilisée par l'app.
Les écritures sont non bloquantes : si le stockage échoue (système de fichiers
éphémère sur Hugging Face Spaces), l'application continue de fonctionner.
"""
import os
from datetime import datetime, date

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bornes.db")


# ─────────────────────────────────────────────────────────────────────────────
# Journal d'usage (best-effort, aucune donnée personnelle)
# ─────────────────────────────────────────────────────────────────────────────
def log_visit():
    """Enregistre une visite (1 fois par session) dans la table `usage_log`.

    Aucune donnée personnelle n'est stockée : uniquement un horodatage serveur.
    Pas d'IP, pas de cookie, pas d'identifiant utilisateur.
    """
    if st.session_state.get("_visit_logged"):
        return
    st.session_state["_visit_logged"] = True
    try:
        import sqlite3
        con = sqlite3.connect(DB_PATH, timeout=2)
        con.execute(
            "CREATE TABLE IF NOT EXISTS usage_log "
            "(ts TEXT NOT NULL, jour TEXT NOT NULL)"
        )
        now = datetime.now()
        con.execute(
            "INSERT INTO usage_log (ts, jour) VALUES (?, ?)",
            (now.isoformat(timespec="seconds"), now.date().isoformat()),
        )
        con.commit()
        con.close()
    except Exception:
        # Monitoring non bloquant : on n'interrompt jamais l'app pour un log.
        pass


def _lire_usage():
    try:
        import sqlite3
        con = sqlite3.connect(DB_PATH, timeout=2)
        df = pd.read_sql("SELECT ts, jour FROM usage_log", con)
        con.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["ts", "jour"])


# ─────────────────────────────────────────────────────────────────────────────
# Indicateurs qualité / fraîcheur
# ─────────────────────────────────────────────────────────────────────────────
def _freshness(bornes):
    """Retourne un dict d'indicateurs de qualité sur la table `bornes`."""
    ind = {}
    ind["nb_bornes"] = 0 if bornes is None else len(bornes)
    if bornes is not None and not bornes.empty:
        ind["nb_arrdt"] = int(bornes["num_arrondissement"].nunique())
        coords_ok = bornes[["latitude", "longitude"]].notna().all(axis=1).mean()
        ind["pct_coords"] = round(coords_ok * 100, 1)
        statut_connu = (bornes["statut_actuel"].astype(str).str.lower() != "inconnu").mean()
        ind["pct_statut"] = round(statut_connu * 100, 1)
    else:
        ind["nb_arrdt"] = 0
        ind["pct_coords"] = 0.0
        ind["pct_statut"] = 0.0
    try:
        ts = datetime.fromtimestamp(os.path.getmtime(DB_PATH))
        ind["build"] = ts.strftime("%Y-%m-%d %H:%M")
    except Exception:
        ind["build"] = "—"
    return ind


def _resultats_modele():
    """Charge les 15 combinaisons scénario × horizon (résultats du modèle)."""
    for path in (
        os.path.join(BASE_DIR, "soutenabilite_scenarios.csv"),
        os.path.join(BASE_DIR, "data", "soutenabilite_scenarios.csv"),
    ):
        if os.path.exists(path):
            try:
                return pd.read_csv(path)
            except Exception:
                return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Onglet Streamlit
# ─────────────────────────────────────────────────────────────────────────────
def render_tab_monitoring(bornes):
    st.markdown("### Suivi & monitoring du projet")
    st.markdown(
        "> Page de supervision : **qualité des données**, **résultats du modèle** "
        "et **usage de l'application**. Elle remplace un serveur de tracking externe "
        "(MLflow) par un suivi léger intégré, cohérent avec un MVP autonome."
    )

    # --- 1. Qualité & fraîcheur des données -----------------------------------
    st.markdown("#### 1. Fraîcheur et qualité des données")
    ind = _freshness(bornes)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Points de charge chargés", f"{ind['nb_bornes']:,}".replace(",", " "))
    c2.metric("Arrondissements couverts", f"{ind['nb_arrdt']} / 20")
    c3.metric("Coordonnées complètes", f"{ind['pct_coords']} %")
    c4.metric("Statut temps réel connu", f"{ind['pct_statut']} %")
    st.caption(f"Dernière génération de la base `bornes.db` : **{ind['build']}** "
               "· source : OpenData Ville de Paris (Belib').")

    # Contrôles de cohérence simples (data quality checks)
    checks = [
        ("20 arrondissements présents", ind["nb_arrdt"] == 20),
        ("Volume de bornes plausible (> 1000)", ind["nb_bornes"] > 1000),
        ("Coordonnées complètes > 95 %", ind["pct_coords"] > 95),
    ]
    st.markdown("**Contrôles automatiques**")
    for libelle, ok in checks:
        st.write(("✅ " if ok else "⚠️ ") + libelle)

    st.markdown("---")

    # --- 2. Résultats du modèle de projection ---------------------------------
    st.markdown("#### 2. Résultats du modèle — 3 scénarios × 5 horizons (15 exécutions)")
    res = _resultats_modele()
    if res is None or res.empty:
        st.info("Résultats de projection non disponibles.")
    else:
        pivot = res.pivot_table(
            index="horizon_years", columns="scenario",
            values="deficit_total", aggfunc="sum",
        )
        cols = [c for c in ["bas", "central", "haut"] if c in pivot.columns]
        pivot = pivot[cols]
        pivot.columns = [c.capitalize() for c in cols]
        pivot.index.name = "Horizon (ans)"
        st.markdown("Déficit de bornes projeté (Paris entier) — sortie principale suivie :")
        st.dataframe(pivot.round(0).astype(int), width='stretch')
        st.caption(
            "Chaque cellule est une exécution reproductible du pipeline de projection "
            "(paramètres : scénario de croissance, horizon, pression cible P*). "
            "Ces indicateurs sont recalculés à chaque build de la base."
        )

    st.markdown("---")

    # --- 3. Usage de l'application --------------------------------------------
    st.markdown("#### 3. Usage de l'application")
    usage = _lire_usage()
    total = len(usage)
    aujourdhui = int((usage["jour"] == date.today().isoformat()).sum()) if total else 0
    u1, u2 = st.columns(2)
    u1.metric("Sessions cumulées", f"{total}")
    u2.metric("Sessions aujourd'hui", f"{aujourdhui}")
    if total:
        par_jour = usage.groupby("jour").size().reset_index(name="sessions")
        st.bar_chart(par_jour, x="jour", y="sessions", height=220)
    st.caption(
        "Journal d'usage anonyme (horodatage serveur uniquement — aucune donnée "
        "personnelle, aucun cookie, aucune IP). Sur Hugging Face Spaces le stockage "
        "est éphémère : le compteur repart à zéro à chaque redémarrage du conteneur."
    )
