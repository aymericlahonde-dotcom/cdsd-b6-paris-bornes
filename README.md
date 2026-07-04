---
title: Paris Bornes
emoji: ⚡
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8501
tags:
- streamlit
pinned: false
short_description: Prioriser l'installation des bornes de recharge VE a Paris
---

# ⚡ Bornes de recharge VE à Paris — Où en installer, combien, et quand ?

Outil d'aide à la décision pour **prioriser l'installation de nouvelles bornes de
recharge pour véhicules électriques (VE) à Paris**, arrondissement par arrondissement.

Projet final — Certification *Concepteur Développeur en Science des Données* (RNCP35288 · Bloc 6).

## 🎯 Problématique

Paris compte aujourd'hui ~1 900 bornes Belib', très inégalement réparties, alors que le
parc de véhicules électriques progresse rapidement. La norme européenne **AFIR** impose
un objectif de **1 borne pour 10 VE** (indicateur de *pression* `P = VE / bornes`).

Le dashboard répond à trois questions :
- **Où** la pression est-elle la plus forte aujourd'hui ?
- **Combien** de bornes manquent à horizon **1 à 5 ans** ?
- **Selon quel scénario** de croissance du parc VE (bas 20 % / central 40 % / haut 60 %) ?

## 🗺️ Fonctionnalités

- **Carte interactive** des ~1 900 bornes Belib' (statut temps réel, puissance, arrondissement).
- **Indicateur de pression** par arrondissement (VERT / AMBRE / ROUGE).
- **Projections** du déficit de bornes par scénario × horizon.
- **Classement** des arrondissements les plus sous-équipés.
- **Volet énergie** : impact de la recharge sur la consommation électrique locale.
- **Suivi & monitoring** : qualité/fraîcheur des données, résultats du modèle (15 exécutions scénario × horizon) et usage anonyme.

## 🔒 RGPD

**Aucune donnée personnelle** n'est traitée : toutes les sources sont ouvertes et agrégées à la
maille arrondissement. Pas de cookie, pas d'authentification, pas d'IP. Le compteur d'usage de la
page monitoring est un horodatage serveur anonyme → hors champ RGPD (art. 4).

## 📊 Données — 100 % sources publiques

| Donnée | Source |
|---|---|
| Bornes (position, puissance) | Belib' statique — **OpenData Ville de Paris** |
| Disponibilité temps réel | Belib' temps réel — **OpenData Ville de Paris** |
| Parc VE, énergie, population, projections | Jeux d'étude du projet (`data/`) |

> Cette version est **totalement autonome** : aucune authentification, aucun secret,
> aucune infrastructure externe. Toutes les données bornes proviennent directement de
> l'API publique OpenData de la Ville de Paris.

## 🏗️ Architecture

```
build_data.py        → génère bornes.db depuis l'OpenData public
bornes.db            → base SQLite embarquée (bornes + pression + population + énergie + VE)
streamlit_app.py     → dashboard (carte, filtres, indicateurs)
streamlit_additions.py → onglets projection / classement / énergie
monitoring.py        → onglet suivi (qualité données, résultats modèle, usage) + journal anonyme
data/                → CSV d'analyse (projections, scénarios, pression)
Dockerfile           → image de déploiement (Hugging Face Spaces)
```

## ▶️ Lancer en local

```bash
pip install -r requirements.txt
python build_data.py      # (optionnel) régénère bornes.db avec les données du jour
streamlit run streamlit_app.py
```

L'application est aussi déployée en ligne sur Hugging Face Spaces (SDK Docker).

## ♻️ Rafraîchir les données

Le bouton **« 🔄 Rafraîchir les données »** dans l'app relance `build_data.py` et
recharge les bornes et leur disponibilité depuis l'OpenData de la Ville de Paris.
