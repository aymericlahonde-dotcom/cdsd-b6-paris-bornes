# Préparation soutenance jury — Bloc 6 · Paris Bornes

> Projet final — Certification *Concepteur Développeur en Science des Données* (RNCP35288, Bloc 6 — Direction de projets en data science).
> Application en ligne : <https://huggingface.co/spaces/Alh92500/paris-bornes> · Code : <https://github.com/aymericlahonde-dotcom/cdsd-b6-paris-bornes>

Ce mémo prépare les 10 minutes de questions/réponses. Il assume une posture honnête :
on présente un **MVP autonome réellement déployé**, tout en assumant une **architecture cible** plus large (vision d'équipe).

---

## 0. Le pitch en 30 secondes
Paris a ~1 900 bornes Belib' très mal réparties, alors que le parc VE explose et que la norme
européenne AFIR impose 1 borne pour 10 VE. Notre outil calcule, **par arrondissement et à 1-5 ans**,
**combien de bornes manquent et où installer en priorité**, selon 3 scénarios de croissance.
Tout est bâti sur des **données 100 % publiques**, déployé en autonomie sur Hugging Face.

---

## 1. RGPD / conformité
**Q : Comment gérez-vous le RGPD ?**
- On ne traite **aucune donnée personnelle**. Toutes les sources sont **ouvertes et agrégées à la maille arrondissement** (20 zones) : Belib' (OpenData Paris), parc VE (SDES/data.gouv), Enedis (conso agrégée), INSEE (population).
- **Aucun traçage** : pas de cookie, pas d'authentification, pas d'IP collectée. Le compteur d'usage de la page monitoring est un simple **horodatage serveur anonyme**, non rattachable à une personne → hors champ de l'article 4 du RGPD.
- **Licences ouvertes** (Licence Ouverte Etalab / ODbL) : réutilisation autorisée, y compris pour l'aide à la décision publique.
- On applique les **principes CNIL** (minimisation, transparence, sécurité : aucun secret dans le dépôt Git). Pas de registre ni de DPO requis puisqu'il n'y a pas de traitement de données personnelles.
- **Si on croisait un jour des données individuelles** (trajets réels d'usagers), il faudrait alors une AIPD/PIA.

## 2. Budget
**Q : Combien ça coûte ?**
- **Solution data (ce qu'on livre) : ~0 €/mois** — Hugging Face Spaces gratuit, OpenData gratuit, GitHub public. Une option CPU/stockage coûterait quelques € /mois, non nécessaire.
- **Coût humain** : équipe de 4 sur 4-5 jours (~15-20 jours-homme).
- **Déploiement métier (ordre de grandeur)** : ~**10-15 k€ par borne** sur voirie (matériel + génie civil + raccordement Enedis) ; borne rapide DC : 30-50 k€ ; maintenance 500-1 500 €/borne/an.
- **Rollout** : le scénario central projette ~**7 600 bornes** à 3 ans → **~90 M€ sur 3 ans**. L'argument ROI : ~0 € de data pour mieux orienter des **dizaines de M€** d'investissement public.

## 3. Choix déterministe vs Machine Learning
**Q : Pourquoi pas de ML ?**
- Le cœur du calcul est une **formule transparente et auditable** : pression = VE / bornes ; cible P* = min(niveau des meilleurs arrondissements, norme AFIR = 10) ; déficit = bornes nécessaires pour atteindre P*.
- **N'importe qui peut refaire le calcul** et le défendre devant un élu — un modèle boîte noire serait plus fragile et moins convaincant sur une décision d'argent public.
- La croissance du parc est traitée par **3 scénarios explicites** (+20/+40/+60 %/an) calibrés sur l'historique d'immatriculations, plutôt qu'une prédiction ponctuelle. C'est un choix **assumé**, pas un manque : on privilégie robustesse et explicabilité.
- *Ouverture ML* : on pourrait ajouter un modèle pour affiner le **placement fin** des bornes (POI, trafic, voirie) — c'est une piste d'amélioration, pas le cœur.

## 4. Monitoring
**Q : Où est le monitoring / comment suivez-vous les résultats ?**
- Onglet **« Suivi & monitoring »** intégré au dashboard, avec 3 familles d'indicateurs :
  1. **Qualité/fraîcheur des données** : nb de bornes chargées (1 900), 20/20 arrondissements couverts, % de coordonnées complètes, contrôles automatiques (data quality checks), date de dernière génération de la base.
  2. **Résultats du modèle** : les **15 exécutions** (3 scénarios × 5 horizons) et leur déficit projeté — c'est la sortie qu'on suit.
  3. **Usage** : compteur de visites anonyme.
- **Honnêteté** : le dossier mentionne MLflow comme brique de l'**architecture cible**. Dans le **MVP livré**, on l'a remplacé par ce **monitoring léger intégré**, plus cohérent avec un déploiement autonome sans serveur externe. (Voir chapitre 13 du dossier.)

## 5. Architecture — cible vs MVP livré
**Q : Le dossier parle d'Airflow, S3, Neon, MLflow, FastAPI, 3 Spaces… c'est déployé ?**
- **Transparence** : ces briques décrivent l'**architecture cible** d'un projet d'équipe complet (industrialisation). Elles ne sont **pas toutes déployées**.
- **Ce qui tourne réellement (MVP)** : OpenData Ville de Paris → nettoyage → **SQLite** → **Streamlit** → **Docker** → **1 seul Hugging Face Space**. Autonome, sans secret, relançable en une commande.
- **Pourquoi** : la consigne du bloc privilégie le **robuste et reproductible** plutôt qu'une automatisation fragile. Le chapitre 13 du dossier fait cette mise au point explicitement.

## 6. Données — extraction, nettoyage, maintenance
**Q : D'où viennent les données et comment on les maintient ?**
- Sources : **API OpenData Ville de Paris** (Belib' statique + temps réel), CSV d'étude pour VE/énergie/population.
- **Extraction** : `build_data.py` télécharge les datasets Belib', déduit l'arrondissement (INSEE 751xx / adresse), harmonise, et écrit `bornes.db`. Aucune authentification.
- **Nettoyage** : suppression des points sans coordonnées/arrondissement, normalisation des statuts, typage numérique.
- **Rafraîchissement** : bouton « Rafraîchir » dans l'app (rejoue le build) + le conteneur reconstruit la base si elle est absente. **Industrialisation** : Airflow planifierait la collecte (cible).

## 7. Leadership / gestion de projet
**Q : Comment le projet a-t-il été mené end-to-end ?**
- Découpage en **4 axes** (Données/forecast, Énergie/réseau, Mobilité/emplacements, Architecture/déploiement), un responsable par axe, sync quotidien.
- **Planning** sur 4-5 jours, livrables par axe, critères de succès technique et métier (chapitre 8-10 du dossier).
- **Décisions assumées** : déterministe > ML, MVP autonome > stack complexe, monitoring léger > MLflow. À chaque fois : robustesse et défendabilité devant un décideur public.

## 8. Impact réel & suites
- **Impact** : prioriser des dizaines de M€ d'investissement bornes, éviter d'aggraver les déserts de recharge, croiser avec la capacité réseau (soutenabilité).
- **Suites** : placement fin par ML (POI/trafic/voirie), industrialisation (Airflow/S3/API), pondération de P* par capacité réseau locale, extension métropole Grand Paris.

---

### Questions pièges anticipées
- *« Vos 3 Spaces sont en ligne ? »* → Non : **un seul** Space (le dashboard). Les 3 Spaces = architecture cible. Assumé, chapitre 13.
- *« Vos runs MLflow ? »* → Remplacés par la page monitoring intégrée. MLflow = cible d'industrialisation.
- *« Où est le ML ? »* → Choix déterministe assumé pour l'explicabilité ; ML = piste sur le placement fin.
- *« Données personnelles ? »* → Aucune. 100 % open data agrégé, hors champ RGPD.
- *« P* = 10, pourquoi ? »* → Norme AFIR (1 borne/10 VE) **et** niveau des arrondissements les mieux équipés : double justification.
