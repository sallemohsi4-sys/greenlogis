"""
calculator.py — Calculateur CO₂ par route logistique
=====================================================
Ce module lit un réseau de livraisons (CSV ou DataFrame) et calcule
pour chaque route les émissions CO₂, le coût carbone, l'intensité
carbone et le niveau de risque environnemental.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from emission_factors import (
    co2_kg,
    cout_carbone_eur,
    intensite_carbone,
    niveau_risque,
    equivalent_voiture,
    get_label_mode,
    get_emoji_mode,
    BENCHMARK_INDUSTRIE_gCO2_TKM,
    FACTEURS_EMISSION,
)

# ─────────────────────────────────────────────────────────────────────────────
# COLONNES REQUISES DANS LE CSV D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────
COLONNES_REQUISES = ["origine", "destination", "mode", "distance_km", "poids_tonnes", "date"]
COLONNES_OPTIONNELLES = ["categorie"]

# Limites raisonnables pour la validation des données
DISTANCE_MAX_KM    = 25_000   # Tour du monde ≈ 40 000 km — on limite à 25 000
POIDS_MAX_TONNES   = 500      # Navires vrac → plusieurs centaines de tonnes
POIDS_MIN_TONNES   = 0.001    # Minimum : 1 kg de marchandise


def charger_csv(chemin_csv: str) -> pd.DataFrame:
    """
    Charge et valide un fichier CSV de routes logistiques.

    Le CSV doit contenir les colonnes :
    origine, destination, mode, distance_km, poids_tonnes, date

    Args:
        chemin_csv : Chemin absolu ou relatif vers le fichier CSV

    Returns:
        DataFrame pandas avec les données validées et nettoyées

    Raises:
        FileNotFoundError : Si le fichier n'existe pas
        ValueError        : Si des colonnes obligatoires sont manquantes
                            ou si les données sont invalides
    """
    try:
        df = pd.read_csv(chemin_csv, encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Fichier CSV introuvable : '{chemin_csv}'. "
            f"Vérifiez le chemin ou utilisez le fichier démo : data/sample_routes.csv"
        )
    except Exception as e:
        raise ValueError(f"Impossible de lire le CSV '{chemin_csv}' : {e}")

    return _valider_dataframe(df)


def _valider_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valide et nettoie un DataFrame de routes.

    Args:
        df : DataFrame brut

    Returns:
        DataFrame nettoyé et validé

    Raises:
        ValueError : Si les données sont invalides ou manquantes
    """
    if df.empty:
        raise ValueError("Le fichier CSV est vide. Ajoutez au moins une route.")

    # Normalisation des noms de colonnes (minuscules, sans espaces)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Vérification des colonnes obligatoires
    colonnes_manquantes = [c for c in COLONNES_REQUISES if c not in df.columns]
    if colonnes_manquantes:
        raise ValueError(
            f"Colonnes manquantes dans le CSV : {', '.join(colonnes_manquantes)}\n"
            f"Colonnes requises : {', '.join(COLONNES_REQUISES)}"
        )

    # Ajout de la colonne optionnelle si absente
    if "categorie" not in df.columns:
        df["categorie"] = "Non spécifié"

    # Suppression des lignes entièrement vides
    df = df.dropna(how="all").reset_index(drop=True)

    # Nettoyage des chaînes de caractères
    for col in ["origine", "destination", "mode"]:
        df[col] = df[col].astype(str).str.strip()

    # Conversion des types numériques
    try:
        df["distance_km"]   = pd.to_numeric(df["distance_km"],   errors="coerce")
        df["poids_tonnes"]  = pd.to_numeric(df["poids_tonnes"],  errors="coerce")
    except Exception as e:
        raise ValueError(f"Erreur de conversion numérique : {e}")

    # Validation des valeurs numériques
    lignes_invalides = df[
        (df["distance_km"].isna()) |
        (df["poids_tonnes"].isna()) |
        (df["distance_km"] <= 0) |
        (df["poids_tonnes"] <= 0) |
        (df["distance_km"] > DISTANCE_MAX_KM) |
        (df["poids_tonnes"] > POIDS_MAX_TONNES)
    ]

    if not lignes_invalides.empty:
        indices = lignes_invalides.index.tolist()
        print(
            f"⚠️  {len(lignes_invalides)} ligne(s) ignorée(s) (données invalides) : "
            f"lignes {[i+2 for i in indices]} du CSV"
        )
        df = df.drop(index=lignes_invalides.index).reset_index(drop=True)

    if df.empty:
        raise ValueError(
            "Aucune donnée valide dans le CSV après validation. "
            "Vérifiez vos données (distances > 0, poids > 0)."
        )

    # Validation des modes de transport
    modes_invalides = df[~df["mode"].isin(FACTEURS_EMISSION.keys())]
    if not modes_invalides.empty:
        modes_inconnus = modes_invalides["mode"].unique().tolist()
        modes_valides  = list(FACTEURS_EMISSION.keys())
        raise ValueError(
            f"Mode(s) de transport inconnu(s) : {modes_inconnus}\n"
            f"Modes valides : {modes_valides}"
        )

    # Conversion de la date (format souple)
    try:
        df["date"] = pd.to_datetime(df["date"], dayfirst=False, errors="coerce")
        nb_dates_invalides = df["date"].isna().sum()
        if nb_dates_invalides > 0:
            print(f"⚠️  {nb_dates_invalides} date(s) non reconnue(s) — remplacement par aujourd'hui")
            df["date"] = df["date"].fillna(pd.Timestamp.now())
    except Exception:
        df["date"] = pd.Timestamp.now()

    return df


def analyser_reseau(source) -> pd.DataFrame:
    """
    Analyse un réseau de livraisons et calcule les indicateurs CO₂ par route.

    Accepte soit un chemin vers un fichier CSV, soit un DataFrame pandas.

    Colonnes ajoutées au DataFrame résultat :
    - co2_kg          : Émissions CO₂ totales de la route (kg)
    - cout_eur        : Coût carbone EU ETS (€)
    - intensite_gco2  : Intensité carbone (gCO₂e/t-km) — KPI GLEC/CSRD
    - niveau_risque   : 'ROUGE', 'ORANGE' ou 'VERT'
    - equivalent_voit : Équivalent km en voiture (lisible)
    - label_mode      : Nom lisible du mode de transport
    - emoji_mode      : Emoji du mode de transport

    Args:
        source : Chemin CSV (str) ou DataFrame pandas

    Returns:
        DataFrame enrichi avec tous les indicateurs calculés

    Raises:
        TypeError   : Si la source n'est pas un str ou DataFrame
        ValueError  : Si les données sont invalides
    """
    # Chargement de la source de données
    if isinstance(source, str):
        df = charger_csv(source)
    elif isinstance(source, pd.DataFrame):
        df = _valider_dataframe(source.copy())
    else:
        raise TypeError(
            f"'source' doit être un chemin CSV (str) ou un DataFrame pandas. "
            f"Reçu : {type(source)}"
        )

    # ── Calcul CO₂ pour chaque route
    co2_list         = []
    cout_list        = []
    intensite_list   = []
    risque_list      = []
    equiv_list       = []

    for _, row in df.iterrows():
        # Calcul des émissions avec la formule GLEC
        c = co2_kg(row["distance_km"], row["poids_tonnes"], row["mode"])
        co2_list.append(round(c, 2))

        # Coût carbone EU ETS
        cout_list.append(round(cout_carbone_eur(c), 2))

        # Intensité carbone (gCO2/t-km)
        intensite = intensite_carbone(c, row["poids_tonnes"], row["distance_km"])
        intensite_list.append(round(intensite, 1))

        # Niveau de risque environnemental
        risque_list.append(niveau_risque(intensite))

        # Équivalent voiture (pédagogique)
        equiv_list.append(equivalent_voiture(c))

    # Ajout des colonnes calculées
    df["co2_kg"]         = co2_list
    df["cout_eur"]       = cout_list
    df["intensite_gco2"] = intensite_list
    df["niveau_risque"]  = risque_list
    df["equivalent_voit"] = equiv_list

    # Ajout des labels lisibles
    df["label_mode"] = df["mode"].apply(get_label_mode)
    df["emoji_mode"] = df["mode"].apply(get_emoji_mode)

    # Identifiant unique de route pour l'UI
    df["id_route"] = [
        f"{row.origine}→{row.destination} ({row.date.strftime('%d/%m')})"
        for _, row in df.iterrows()
    ]

    return df


def resume_reseau(df: pd.DataFrame) -> dict:
    """
    Calcule le résumé global du réseau logistique analysé.

    Retourne un dictionnaire avec tous les KPIs nécessaires pour :
    - Le tableau de bord Streamlit
    - La génération du rapport ESG PDF
    - L'analyse IA par Claude

    Args:
        df : DataFrame enrichi produit par analyser_reseau()

    Returns:
        Dictionnaire avec les clés :
        - total_co2_kg          : Émissions totales du réseau (kg)
        - total_co2_tonnes      : Émissions totales (tonnes, pour rapport)
        - total_cout_eur        : Coût carbone total (€)
        - nb_routes             : Nombre de routes dans le réseau
        - distance_totale_km    : Distance totale parcourue (km)
        - poids_total_tonnes    : Poids total transporté (tonnes)
        - tonne_km_total        : Tonne-kilomètres totaux
        - intensite_moyenne     : Intensité carbone moyenne (gCO2/t-km)
        - route_plus_polluante  : Info sur la route la plus émettrice
        - mode_le_plus_utilise  : Mode dominant (par CO₂)
        - repartition_co2_mode  : Dict mode → % du CO₂ total
        - nb_rouge/orange/vert  : Nombre de routes par niveau
        - benchmark_delta       : Écart vs benchmark industrie (%)
        - score_environnemental : Score 0-100 (100 = parfait)
        - periode               : Plage de dates des données

    Raises:
        ValueError : Si le DataFrame est vide ou ne contient pas co2_kg
    """
    if df.empty:
        raise ValueError("Impossible de calculer le résumé : DataFrame vide.")

    if "co2_kg" not in df.columns:
        raise ValueError(
            "Le DataFrame ne contient pas la colonne 'co2_kg'. "
            "Appelez d'abord analyser_reseau()."
        )

    # ── KPIs principaux
    total_co2_kg     = df["co2_kg"].sum()
    total_cout_eur   = df["cout_eur"].sum()
    nb_routes        = len(df)
    dist_totale      = df["distance_km"].sum()
    poids_total      = df["poids_tonnes"].sum()
    tonne_km_total   = (df["distance_km"] * df["poids_tonnes"]).sum()

    # ── Intensité moyenne pondérée par tonne-km (standard GLEC)
    if tonne_km_total > 0:
        intensite_moy = (total_co2_kg * 1000.0) / tonne_km_total
    else:
        intensite_moy = 0.0

    # ── Route la plus polluante
    idx_max = df["co2_kg"].idxmax()
    route_top = df.loc[idx_max]
    route_plus_polluante = {
        "id_route":   route_top.get("id_route", "N/A"),
        "origine":    route_top["origine"],
        "destination": route_top["destination"],
        "mode":       route_top["label_mode"],
        "co2_kg":     round(route_top["co2_kg"], 1),
        "pct_total":  round(route_top["co2_kg"] / total_co2_kg * 100, 1) if total_co2_kg > 0 else 0,
    }

    # ── Mode le plus utilisé (par CO₂ total émis)
    co2_par_mode      = df.groupby("mode")["co2_kg"].sum()
    mode_dominant     = co2_par_mode.idxmax() if not co2_par_mode.empty else "N/A"
    label_dominant    = get_label_mode(mode_dominant)

    # ── Répartition CO₂ par mode (en %)
    repartition = {}
    for mode_key, co2_val in co2_par_mode.items():
        pct = round(co2_val / total_co2_kg * 100, 1) if total_co2_kg > 0 else 0
        repartition[get_label_mode(mode_key)] = {
            "co2_kg": round(co2_val, 1),
            "pct": pct,
            "emoji": get_emoji_mode(mode_key),
        }

    # ── Répartition par niveau de risque
    nb_rouge  = int((df["niveau_risque"] == "ROUGE").sum())
    nb_orange = int((df["niveau_risque"] == "ORANGE").sum())
    nb_vert   = int((df["niveau_risque"] == "VERT").sum())

    # ── Benchmark vs industrie
    benchmark_delta = 0.0
    if BENCHMARK_INDUSTRIE_gCO2_TKM > 0:
        benchmark_delta = (
            (intensite_moy - BENCHMARK_INDUSTRIE_gCO2_TKM) / BENCHMARK_INDUSTRIE_gCO2_TKM * 100
        )

    # ── Score environnemental (0-100)
    # Basé sur l'intensité carbone : 0 gCO2/t-km = 100/100, 300 gCO2/t-km = 0/100
    score_max_intensity = 300.0  # Seuil "catastrophique"
    score = max(0.0, min(100.0, (1 - intensite_moy / score_max_intensity) * 100))

    # Bonus si en dessous du benchmark industrie
    if intensite_moy < BENCHMARK_INDUSTRIE_gCO2_TKM:
        score = min(100.0, score + 5)

    score = round(score, 1)

    # ── Période des données
    if "date" in df.columns and not df["date"].isna().all():
        date_debut = df["date"].min()
        date_fin   = df["date"].max()
        periode = f"{date_debut.strftime('%d/%m/%Y')} → {date_fin.strftime('%d/%m/%Y')}"
    else:
        periode = "Période non spécifiée"

    return {
        # KPIs principaux
        "total_co2_kg":         round(total_co2_kg, 1),
        "total_co2_tonnes":     round(total_co2_kg / 1000, 3),
        "total_cout_eur":       round(total_cout_eur, 2),
        "nb_routes":            nb_routes,
        "distance_totale_km":   round(dist_totale, 0),
        "poids_total_tonnes":   round(poids_total, 1),
        "tonne_km_total":       round(tonne_km_total, 0),
        "intensite_moyenne":    round(intensite_moy, 1),

        # Routes remarquables
        "route_plus_polluante": route_plus_polluante,
        "mode_le_plus_utilise": label_dominant,
        "repartition_co2_mode": repartition,

        # Niveaux de risque
        "nb_rouge":   nb_rouge,
        "nb_orange":  nb_orange,
        "nb_vert":    nb_vert,

        # Benchmark
        "benchmark_delta":      round(benchmark_delta, 1),
        "benchmark_industrie":  BENCHMARK_INDUSTRIE_gCO2_TKM,

        # Score global
        "score_environnemental": score,

        # Période
        "periode": periode,

        # Informations complémentaires pour le rapport ESG
        "equivalent_voitures_km":  round(total_co2_kg / 0.12, 0),
        "equivalent_vols_paris_ny": round(total_co2_kg / 900, 2),
    }


def top_routes_polluantes(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Retourne les N routes les plus émettrices en CO₂.

    Args:
        df : DataFrame enrichi
        n  : Nombre de routes à retourner (défaut : 5)

    Returns:
        DataFrame trié par co2_kg décroissant, limité à n lignes
    """
    cols = ["origine", "destination", "mode", "distance_km",
            "poids_tonnes", "co2_kg", "cout_eur", "intensite_gco2",
            "niveau_risque", "equivalent_voit"]
    cols_dispo = [c for c in cols if c in df.columns]
    return df.nlargest(n, "co2_kg")[cols_dispo].reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# TEST RAPIDE
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os

    chemin_demo = os.path.join(os.path.dirname(__file__), "data", "sample_routes.csv")

    print("=" * 65)
    print("TEST — Analyse réseau logistique démo")
    print("=" * 65)

    try:
        df_analyse = analyser_reseau(chemin_demo)
        print(f"\n✅ {len(df_analyse)} routes chargées et analysées\n")
        print(df_analyse[["origine", "destination", "mode", "co2_kg",
                           "intensite_gco2", "niveau_risque"]].to_string(index=False))

        print("\n" + "─" * 65)
        res = resume_reseau(df_analyse)
        print(f"📊 CO₂ total réseau   : {res['total_co2_kg']:,.1f} kg")
        print(f"💰 Coût carbone total : {res['total_cout_eur']:,.2f} €")
        print(f"🌿 Score environnemental : {res['score_environnemental']}/100")
        print(f"📍 Route la plus polluante : {res['route_plus_polluante']['id_route']}")
        print(f"   → {res['route_plus_polluante']['co2_kg']} kg CO₂ "
              f"({res['route_plus_polluante']['pct_total']}% du total)")

    except Exception as e:
        print(f"❌ Erreur : {e}")
