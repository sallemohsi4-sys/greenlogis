"""
optimizer.py — Algorithmes d'optimisation logistique verte
===========================================================
Trois algorithmes pour réduire l'empreinte carbone d'un réseau :
  1. Consolidation de chargements (mutualisation des camions)
  2. Report modal — Modal Shift (camion → train/bateau)
  3. Électrification des routes (diesel → électrique)
"""

import pandas as pd
import numpy as np
from itertools import combinations
from datetime import timedelta
from emission_factors import (
    co2_kg as calc_co2,
    cout_carbone_eur,
    FACTEURS_EMISSION,
    DISTANCE_MIN_MODAL_SHIFT_KM,
    DISTANCE_MAX_EV_KM,
    get_label_mode,
)

# ─────────────────────────────────────────────────────────────────────────────
# PARAMÈTRES DES ALGORITHMES
# ─────────────────────────────────────────────────────────────────────────────

# Algorithme 1 — Consolidation
CAPACITE_CAMION_TONNES      = 24.0   # Capacité utile max d'un semi-remorque (t)
FENETRE_TEMPORELLE_JOURS    = 1      # ±1 jour de flexibilité sur les dates
DISTANCE_DESTINATIONS_PROCHES = 80   # km max entre deux destinations "proches"

# Algorithme 2 — Modal shift
DELAI_SUPPLEMENTAIRE_TRAIN  = 0.20   # Train = +20% de temps de transit en moyenne
COUT_SUPPLEMENTAIRE_TRAIN   = 0.10   # Train légèrement moins cher (-10%) sur longue distance

# Algorithme 3 — Électrification
MIX_ELECTRIQUE_EU_FACTEUR   = 0.52   # Réduction CO₂ vs diesel (mix EU moyen)
MIX_ELECTRIQUE_FR_FACTEUR   = 0.95   # France : quasi nucléaire (95% moins polluant)

# Modes "camion diesel" ciblés par les algorithmes
MODES_CAMION_DIESEL = ["camion_diesel_grand", "camion_diesel_moyen", "camion_diesel_petit"]


# ─────────────────────────────────────────────────────────────────────────────
# ALGORITHME 1 — CONSOLIDATION DE CHARGEMENTS
# ─────────────────────────────────────────────────────────────────────────────

def detecter_consolidations(df: pd.DataFrame) -> list:
    """
    Détecte les opportunités de consolidation de chargements.

    Logique de consolidation :
    - Même origine (exact)
    - Même destination OU destinations proches (<80 km)
      [approximation : on utilise la même destination pour le démo]
    - Fenêtre temporelle : dates à ±1 jour
    - Poids combiné ≤ 24 tonnes (capacité d'un semi-remorque)

    Pour chaque paire de routes consolidables, calcule :
    - CO₂ économisé : émission d'un seul trajet vs deux trajets séparés
    - Économie financière (EU ETS)
    - Contraintes à vérifier (délai, conditions de stockage)

    Args:
        df : DataFrame enrichi produit par analyser_reseau()

    Returns:
        Liste de dictionnaires, chaque dict décrit une opportunité :
        {
          "id": str,
          "route_1": dict, "route_2": dict,
          "origines": str, "destinations": str,
          "poids_combine": float,
          "co2_avant": float, "co2_apres": float,
          "co2_economise": float, "pct_reduction": float,
          "economie_eur": float,
          "faisabilite": str,  # "FACILE", "MOYEN", "DIFFICILE"
          "contraintes": list,
        }
    """
    if df.empty or "co2_kg" not in df.columns:
        return []

    # Filtrer uniquement les camions diesel (candidats à la consolidation)
    df_camion = df[df["mode"].isin(MODES_CAMION_DIESEL)].copy()
    df_camion = df_camion.reset_index(drop=True)

    if len(df_camion) < 2:
        return []

    opportunites = []
    paires_traitees = set()

    for i, j in combinations(df_camion.index, 2):
        # Éviter les doublons
        cle_paire = tuple(sorted([i, j]))
        if cle_paire in paires_traitees:
            continue

        route_a = df_camion.loc[i]
        route_b = df_camion.loc[j]

        # ── Critère 1 : Même origine
        if route_a["origine"].strip().lower() != route_b["origine"].strip().lower():
            continue

        # ── Critère 2 : Même destination ou proches
        # (Simplification : même destination dans cette version)
        if route_a["destination"].strip().lower() != route_b["destination"].strip().lower():
            continue

        # ── Critère 3 : Fenêtre temporelle ±1 jour
        try:
            date_a = pd.to_datetime(route_a["date"])
            date_b = pd.to_datetime(route_b["date"])
            delta_jours = abs((date_a - date_b).days)
            if delta_jours > FENETRE_TEMPORELLE_JOURS:
                continue
        except Exception:
            continue

        # ── Critère 4 : Poids combiné ≤ capacité camion
        poids_combine = route_a["poids_tonnes"] + route_b["poids_tonnes"]
        if poids_combine > CAPACITE_CAMION_TONNES:
            continue

        # ── Calcul du gain CO₂
        # Avant consolidation : 2 trajets séparés
        co2_avant = route_a["co2_kg"] + route_b["co2_kg"]

        # Après consolidation : 1 seul trajet avec poids combiné
        # On utilise le camion grand (plus efficace à pleine charge)
        co2_apres = calc_co2(
            route_a["distance_km"],
            poids_combine,
            "camion_diesel_grand"
        )

        co2_economise = co2_avant - co2_apres
        pct_reduction = (co2_economise / co2_avant * 100) if co2_avant > 0 else 0
        economie_eur  = cout_carbone_eur(co2_economise)

        if co2_economise <= 0:
            continue  # Pas de gain = pas d'opportunité

        # ── Évaluation de la faisabilité
        contraintes = []
        if delta_jours > 0:
            contraintes.append(f"Décalage de {delta_jours} jour(s) à négocier avec le client")
        if poids_combine > 20:
            contraintes.append("Poids proche de la capacité max — vérifier le chargement")
        if route_a.get("categorie", "") != route_b.get("categorie", ""):
            cat_a = route_a.get("categorie", "N/A")
            cat_b = route_b.get("categorie", "N/A")
            contraintes.append(
                f"Catégories différentes ({cat_a} + {cat_b}) — compatibilité à vérifier"
            )

        if len(contraintes) == 0:
            faisabilite = "FACILE"
        elif len(contraintes) == 1:
            faisabilite = "MOYEN"
        else:
            faisabilite = "DIFFICILE"

        opportunites.append({
            "id":            f"CONSOL-{len(opportunites)+1:02d}",
            "route_1": {
                "id":          i,
                "origine":     route_a["origine"],
                "destination": route_a["destination"],
                "mode":        get_label_mode(route_a["mode"]),
                "poids":       route_a["poids_tonnes"],
                "date":        str(route_a["date"])[:10],
                "co2_kg":      round(route_a["co2_kg"], 1),
            },
            "route_2": {
                "id":          j,
                "origine":     route_b["origine"],
                "destination": route_b["destination"],
                "mode":        get_label_mode(route_b["mode"]),
                "poids":       route_b["poids_tonnes"],
                "date":        str(route_b["date"])[:10],
                "co2_kg":      round(route_b["co2_kg"], 1),
            },
            "origines":       route_a["origine"],
            "destinations":   route_a["destination"],
            "poids_combine":  round(poids_combine, 1),
            "taux_remplissage": round(poids_combine / CAPACITE_CAMION_TONNES * 100, 1),
            "co2_avant":      round(co2_avant, 1),
            "co2_apres":      round(co2_apres, 1),
            "co2_economise":  round(co2_economise, 1),
            "pct_reduction":  round(pct_reduction, 1),
            "economie_eur":   round(economie_eur, 2),
            "faisabilite":    faisabilite,
            "contraintes":    contraintes,
        })

        paires_traitees.add(cle_paire)

    # Trier par CO₂ économisé décroissant
    opportunites.sort(key=lambda x: x["co2_economise"], reverse=True)
    return opportunites


# ─────────────────────────────────────────────────────────────────────────────
# ALGORITHME 2 — MODAL SHIFT (REPORT MODAL)
# ─────────────────────────────────────────────────────────────────────────────

def detecter_modal_shifts(df: pd.DataFrame) -> list:
    """
    Identifie les routes camion qui bénéficieraient d'un report modal.

    Critère principal : routes camion diesel > 300 km
    Alternatives analysées :
    - Train électrique (réseau EU, 18 gCO2/t-km)
    - Train électrique France si l'une des villes est en France (4 gCO2/t-km)
    - Camion électrique si distance < 400 km

    Pour chaque route candidate, calcule :
    - CO₂ économisé par alternative
    - Délai supplémentaire estimé
    - Différence de coût carbone

    Args:
        df : DataFrame enrichi produit par analyser_reseau()

    Returns:
        Liste de dictionnaires décrivant chaque opportunité de report modal
    """
    if df.empty or "co2_kg" not in df.columns:
        return []

    # Villes approximativement en France (pour bonus train nucléaire)
    villes_france = {
        "paris", "lyon", "marseille", "toulouse", "bordeaux",
        "nantes", "strasbourg", "lille", "grenoble", "rennes",
        "nice", "montpellier", "dijon", "reims", "rouen"
    }

    modal_shifts = []

    for idx, row in df.iterrows():
        # Uniquement les camions diesel sur longue distance
        if row["mode"] not in MODES_CAMION_DIESEL:
            continue
        if row["distance_km"] < DISTANCE_MIN_MODAL_SHIFT_KM:
            continue

        co2_actuel = row["co2_kg"]
        alternatives = []

        # ── Alternative 1 : Train électrique EU
        co2_train_eu = calc_co2(row["distance_km"], row["poids_tonnes"], "train_electrique")
        economies_eu = co2_actuel - co2_train_eu
        if economies_eu > 0:
            alternatives.append({
                "mode_cible":     "Train électrique EU",
                "mode_key":       "train_electrique",
                "co2_cible_kg":   round(co2_train_eu, 1),
                "co2_economise":  round(economies_eu, 1),
                "pct_reduction":  round(economies_eu / co2_actuel * 100, 1),
                "economie_eur":   round(cout_carbone_eur(economies_eu), 2),
                "delai_supp_pct": f"+{int(DELAI_SUPPLEMENTAIRE_TRAIN*100)}% temps de transit",
                "note":           "Recommandé pour distances > 500 km",
            })

        # ── Alternative 2 : Train électrique France (si applicable)
        orig_lower = row["origine"].lower()
        dest_lower = row["destination"].lower()
        route_france = orig_lower in villes_france or dest_lower in villes_france

        if route_france:
            co2_train_fr = calc_co2(row["distance_km"], row["poids_tonnes"], "train_electrique_france")
            economies_fr = co2_actuel - co2_train_fr
            if economies_fr > 0:
                alternatives.append({
                    "mode_cible":     "Train électrique France 🇫🇷",
                    "mode_key":       "train_electrique_france",
                    "co2_cible_kg":   round(co2_train_fr, 1),
                    "co2_economise":  round(economies_fr, 1),
                    "pct_reduction":  round(economies_fr / co2_actuel * 100, 1),
                    "economie_eur":   round(cout_carbone_eur(economies_fr), 2),
                    "delai_supp_pct": f"+{int(DELAI_SUPPLEMENTAIRE_TRAIN*100)}% temps de transit",
                    "note":           "⭐ Meilleure option — réseau ferré français décarbonisé",
                })

        # ── Alternative 3 : Camion électrique (si distance ≤ 400 km)
        if row["distance_km"] <= DISTANCE_MAX_EV_KM:
            co2_ev = calc_co2(row["distance_km"], row["poids_tonnes"], "camion_electrique")
            economies_ev = co2_actuel - co2_ev
            if economies_ev > 0:
                alternatives.append({
                    "mode_cible":     "Camion électrique ⚡",
                    "mode_key":       "camion_electrique",
                    "co2_cible_kg":   round(co2_ev, 1),
                    "co2_economise":  round(economies_ev, 1),
                    "pct_reduction":  round(economies_ev / co2_actuel * 100, 1),
                    "economie_eur":   round(cout_carbone_eur(economies_ev), 2),
                    "delai_supp_pct": "Aucun délai supplémentaire",
                    "note":           "Nécessite infrastructure de recharge",
                })

        if not alternatives:
            continue

        # Meilleure alternative = max économies CO₂
        meilleure = max(alternatives, key=lambda x: x["co2_economise"])

        modal_shifts.append({
            "id":                f"MODAL-{len(modal_shifts)+1:02d}",
            "origine":           row["origine"],
            "destination":       row["destination"],
            "mode_actuel":       get_label_mode(row["mode"]),
            "distance_km":       row["distance_km"],
            "poids_tonnes":      row["poids_tonnes"],
            "co2_actuel_kg":     round(co2_actuel, 1),
            "cout_actuel_eur":   round(cout_carbone_eur(co2_actuel), 2),
            "alternatives":      alternatives,
            "meilleure_option":  meilleure,
            "route_france":      route_france,
        })

    # Trier par CO₂ économisé (meilleure alternative) décroissant
    modal_shifts.sort(
        key=lambda x: x["meilleure_option"]["co2_economise"],
        reverse=True
    )
    return modal_shifts


# ─────────────────────────────────────────────────────────────────────────────
# ALGORITHME 3 — EV ROUTING (ÉLECTRIFICATION)
# ─────────────────────────────────────────────────────────────────────────────

def detecter_ev_routes(df: pd.DataFrame) -> list:
    """
    Identifie les routes camion diesel éligibles à l'électrification.

    Critère : routes camion diesel ≤ 400 km
    Calcule : réduction CO₂ selon mix électrique du pays de destination,
              estimation économie carburant.

    Args:
        df : DataFrame enrichi

    Returns:
        Liste des routes EV-éligibles avec économies potentielles
    """
    if df.empty or "co2_kg" not in df.columns:
        return []

    # Pays/villes à mix électrique très propre
    zones_propres = {"paris", "lyon", "marseille", "france", "suisse", "suède", "norway"}

    ev_routes = []

    for idx, row in df.iterrows():
        if row["mode"] not in MODES_CAMION_DIESEL:
            continue
        if row["distance_km"] > DISTANCE_MAX_EV_KM:
            continue

        co2_diesel = row["co2_kg"]

        # Mix électrique selon destination
        dest_lower = row["destination"].lower()
        if any(z in dest_lower for z in zones_propres):
            reduction_pct = MIX_ELECTRIQUE_FR_FACTEUR
            mix_label = "mix propre (≥95%)"
        else:
            reduction_pct = MIX_ELECTRIQUE_EU_FACTEUR
            mix_label = "mix EU moyen (52%)"

        co2_ev = calc_co2(row["distance_km"], row["poids_tonnes"], "camion_electrique")
        co2_economise = co2_diesel - co2_ev

        # Estimation économie carburant (diesel ≈ 35L/100km pour grand camion)
        cout_diesel_estime = row["distance_km"] * 0.35 * 1.60  # 35L/100km × 1.60€/L
        cout_elec_estime   = row["distance_km"] * 0.35 * 0.35  # kWh × 0.35€/kWh (tarif pro)
        economie_carburant = cout_diesel_estime - cout_elec_estime

        if co2_economise <= 0:
            continue

        ev_routes.append({
            "id":               f"EV-{len(ev_routes)+1:02d}",
            "origine":          row["origine"],
            "destination":      row["destination"],
            "mode_actuel":      get_label_mode(row["mode"]),
            "distance_km":      row["distance_km"],
            "poids_tonnes":     row["poids_tonnes"],
            "co2_diesel_kg":    round(co2_diesel, 1),
            "co2_ev_kg":        round(co2_ev, 1),
            "co2_economise":    round(co2_economise, 1),
            "pct_reduction":    round(co2_economise / co2_diesel * 100, 1),
            "economie_carbone_eur": round(cout_carbone_eur(co2_economise), 2),
            "economie_carburant_eur": round(economie_carburant, 0),
            "mix_electrique":   mix_label,
            "autonomie_ok":     row["distance_km"] <= DISTANCE_MAX_EV_KM,
        })

    ev_routes.sort(key=lambda x: x["co2_economise"], reverse=True)
    return ev_routes


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHÈSE GLOBALE DES OPTIMISATIONS
# ─────────────────────────────────────────────────────────────────────────────

def synthese_optimisations(
    df: pd.DataFrame,
    consolidations: list,
    modal_shifts: list,
    ev_routes: list
) -> dict:
    """
    Calcule le bilan global de toutes les optimisations identifiées.

    Permet d'afficher le résumé "Potentiel total de réduction" dans le dashboard
    et dans le rapport ESG.

    Args:
        df             : DataFrame enrichi (réseau actuel)
        consolidations : Liste produite par detecter_consolidations()
        modal_shifts   : Liste produite par detecter_modal_shifts()
        ev_routes      : Liste produite par detecter_ev_routes()

    Returns:
        Dictionnaire avec :
        - co2_total_actuel    : CO₂ du réseau actuel (kg)
        - co2_consolid_eco    : Économie consolidation (kg)
        - co2_modal_eco       : Économie meilleur modal shift (kg)
        - co2_ev_eco          : Économie électrification (kg)
        - co2_total_eco       : Économie totale cumulée (kg) [sans double comptage]
        - pct_reduction_total : % de réduction sur le réseau total
        - score_optim_global  : % du potentiel d'optimisation mobilisé
        - top_3_actions       : 3 actions prioritaires (ROI CO₂/€ le plus élevé)
        - economie_eur_totale : Économie financière totale (EU ETS)
    """
    co2_total = df["co2_kg"].sum() if "co2_kg" in df.columns else 0.0

    # ── Gains consolidation
    co2_consolid_eco = sum(c["co2_economise"] for c in consolidations)

    # ── Gains modal shift (meilleure option par route, sans doublons avec EV)
    routes_modal_ids = set()
    co2_modal_eco = 0.0
    for ms in modal_shifts:
        # Éviter de compter deux fois les routes EV déjà comptées en modal shift
        cle = f"{ms['origine']}_{ms['destination']}"
        if cle not in routes_modal_ids:
            co2_modal_eco += ms["meilleure_option"]["co2_economise"]
            routes_modal_ids.add(cle)

    # ── Gains EV (uniquement routes non comptées en modal shift)
    co2_ev_eco = 0.0
    for ev in ev_routes:
        cle = f"{ev['origine']}_{ev['destination']}"
        if cle not in routes_modal_ids:  # Pas de double comptage
            co2_ev_eco += ev["co2_economise"]

    # ── Total (avec plafonnement à 100% du CO₂ actuel)
    co2_total_eco = min(co2_consolid_eco + co2_modal_eco + co2_ev_eco, co2_total)
    pct_reduction = (co2_total_eco / co2_total * 100) if co2_total > 0 else 0.0

    # ── Économie financière
    economie_eur = cout_carbone_eur(co2_total_eco)

    # ── Top 3 actions (ratio CO₂ économisé le plus élevé)
    toutes_actions = []

    for c in consolidations:
        toutes_actions.append({
            "type":          "Consolidation",
            "description":   f"Consolider {c['origines']} → {c['destinations']}",
            "co2_economise": c["co2_economise"],
            "economie_eur":  c["economie_eur"],
            "faisabilite":   c["faisabilite"],
            "id":            c["id"],
        })

    for ms in modal_shifts:
        opt = ms["meilleure_option"]
        toutes_actions.append({
            "type":          "Report modal",
            "description":   f"{ms['origine']} → {ms['destination']} via {opt['mode_cible']}",
            "co2_economise": opt["co2_economise"],
            "economie_eur":  opt["economie_eur"],
            "faisabilite":   "MOYEN",
            "id":            ms["id"],
        })

    for ev in ev_routes:
        toutes_actions.append({
            "type":          "Électrification",
            "description":   f"{ev['origine']} → {ev['destination']} en camion électrique",
            "co2_economise": ev["co2_economise"],
            "economie_eur":  ev["economie_carbone_eur"],
            "faisabilite":   "FACILE",
            "id":            ev["id"],
        })

    # Trier par CO₂ économisé décroissant
    toutes_actions.sort(key=lambda x: x["co2_economise"], reverse=True)
    top_3 = toutes_actions[:3]

    # Score d'optimisation : % du potentiel identifié sur le total
    score_optim = round(pct_reduction, 1)

    return {
        "co2_total_actuel":    round(co2_total, 1),
        "co2_consolid_eco":    round(co2_consolid_eco, 1),
        "co2_modal_eco":       round(co2_modal_eco, 1),
        "co2_ev_eco":          round(co2_ev_eco, 1),
        "co2_total_eco":       round(co2_total_eco, 1),
        "pct_reduction_total": round(pct_reduction, 1),
        "score_optim_global":  score_optim,
        "economie_eur_totale": round(economie_eur, 2),
        "top_3_actions":       top_3,
        "nb_consolidations":   len(consolidations),
        "nb_modal_shifts":     len(modal_shifts),
        "nb_ev_routes":        len(ev_routes),
    }


def optimiser_reseau(df: pd.DataFrame) -> dict:
    """
    Fonction principale — lance tous les algorithmes d'optimisation.

    Point d'entrée unique pour l'application Streamlit et le module advisor.

    Args:
        df : DataFrame enrichi produit par analyser_reseau()

    Returns:
        Dictionnaire complet avec :
        - consolidations : liste des opportunités de consolidation
        - modal_shifts   : liste des opportunités de report modal
        - ev_routes      : liste des routes EV-éligibles
        - synthese       : bilan global (voir synthese_optimisations)
    """
    consolidations = detecter_consolidations(df)
    modal_shifts   = detecter_modal_shifts(df)
    ev_routes      = detecter_ev_routes(df)
    synthese       = synthese_optimisations(df, consolidations, modal_shifts, ev_routes)

    return {
        "consolidations": consolidations,
        "modal_shifts":   modal_shifts,
        "ev_routes":      ev_routes,
        "synthese":       synthese,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEST RAPIDE
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from calculator import analyser_reseau

    chemin_demo = os.path.join(os.path.dirname(__file__), "data", "sample_routes.csv")

    print("=" * 65)
    print("TEST — Algorithmes d'optimisation")
    print("=" * 65)

    try:
        df = analyser_reseau(chemin_demo)
        resultats = optimiser_reseau(df)
        s = resultats["synthese"]

        print(f"\n📊 CO₂ réseau actuel : {s['co2_total_actuel']:,.1f} kg")
        print(f"\n✅ Consolidations détectées    : {s['nb_consolidations']}")
        print(f"   → Économie : {s['co2_consolid_eco']:,.1f} kg CO₂")
        print(f"\n🚆 Modal shifts détectés       : {s['nb_modal_shifts']}")
        print(f"   → Économie : {s['co2_modal_eco']:,.1f} kg CO₂")
        print(f"\n⚡ Routes EV-éligibles         : {s['nb_ev_routes']}")
        print(f"   → Économie : {s['co2_ev_eco']:,.1f} kg CO₂")
        print(f"\n🎯 RÉDUCTION TOTALE ATTEIGNABLE : {s['pct_reduction_total']:.1f}%")
        print(f"💰 Économie financière          : {s['economie_eur_totale']:,.2f} €")

        print(f"\n🏆 TOP 3 ACTIONS PRIORITAIRES :")
        for i, action in enumerate(s["top_3_actions"], 1):
            print(f"  {i}. [{action['type']}] {action['description']}")
            print(f"     → {action['co2_economise']:,.1f} kg CO₂ | {action['economie_eur']:.2f} €")

    except Exception as e:
        print(f"❌ Erreur : {e}")
        raise
