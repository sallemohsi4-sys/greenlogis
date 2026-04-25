"""
emission_factors.py — Facteurs d'émission officiels GLEC Framework 2023
=======================================================================
Source : Global Logistics Emissions Council (GLEC) Framework v3.0
         Smart Freight Centre, 2023
         https://www.smartfreightcentre.org/en/our-programs/global-logistics-emissions-council/

Ce module centralise tous les facteurs d'émission utilisés dans l'application.
Toutes les valeurs sont en gCO2e par tonne-kilomètre (gCO2e/t-km).
"""

# ─────────────────────────────────────────────────────────────────────────────
# FACTEURS D'ÉMISSION — Source : GLEC Framework 2023 (gCO2e / tonne-km)
# ─────────────────────────────────────────────────────────────────────────────
FACTEURS_EMISSION = {
    # ── Camions routiers (Well-to-Wheel, inclut extraction du carburant)
    "camion_diesel_grand":    96,    # >32t GVW (Gross Vehicle Weight) — longue distance
    "camion_diesel_moyen":   120,    # 16-32t GVW — régional
    "camion_diesel_petit":   200,    # <16t GVW — livraison urbaine
    "camion_electrique":      50,    # Dépend du mix électrique national (moyenne EU)

    # ── Transport ferroviaire
    "train_diesel":           28,    # Train de fret diesel
    "train_electrique":       18,    # Moyenne réseau européen
    "train_electrique_france": 4,    # France = nucléaire = très faible intensité carbone

    # ── Transport maritime
    "bateau_conteneur":       16,    # Porte-conteneurs (grands navires)
    "bateau_vrac":             8,    # Vraquier (vrac sec/liquide)

    # ── Transport aérien
    "avion_fret":            602,    # Fret aérien — 6x plus polluant que le camion
}

# ─────────────────────────────────────────────────────────────────────────────
# LABELS LISIBLES — Pour l'interface utilisateur et les rapports
# ─────────────────────────────────────────────────────────────────────────────
LABELS_MODES = {
    "camion_diesel_grand":     "Camion diesel (>32t)",
    "camion_diesel_moyen":     "Camion diesel (16-32t)",
    "camion_diesel_petit":     "Camion diesel (<16t)",
    "camion_electrique":       "Camion électrique",
    "train_diesel":            "Train diesel",
    "train_electrique":        "Train électrique (EU)",
    "train_electrique_france": "Train électrique (France)",
    "bateau_conteneur":        "Bateau porte-conteneurs",
    "bateau_vrac":             "Bateau vraquier",
    "avion_fret":              "Avion cargo",
}

# Emojis associés à chaque mode (pour l'interface)
EMOJIS_MODES = {
    "camion_diesel_grand":     "🚛",
    "camion_diesel_moyen":     "🚚",
    "camion_diesel_petit":     "🚐",
    "camion_electrique":       "⚡🚛",
    "train_diesel":            "🚂",
    "train_electrique":        "🚆",
    "train_electrique_france": "🚆🇫🇷",
    "bateau_conteneur":        "🚢",
    "bateau_vrac":             "⛴️",
    "avion_fret":              "✈️",
}

# ─────────────────────────────────────────────────────────────────────────────
# PRIX DU CARBONE — Marché EU ETS (Emissions Trading System)
# ─────────────────────────────────────────────────────────────────────────────
PRIX_CARBONE_EUR_TONNE = 65.0   # Prix EU ETS moyen 2024 (€/tonne CO2)
PRIX_CARBONE_EUR_KG    = PRIX_CARBONE_EUR_TONNE / 1000.0  # = 0.065 €/kg CO2

# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARKS SECTORIELS — Référence pour comparaison
# ─────────────────────────────────────────────────────────────────────────────
BENCHMARK_INDUSTRIE_gCO2_TKM = 85.0  # Moyenne industrie logistique (gCO2e/t-km)

# ─────────────────────────────────────────────────────────────────────────────
# ÉQUIVALENCES PÉDAGOGIQUES — Pour rendre les chiffres concrets
# ─────────────────────────────────────────────────────────────────────────────
CO2_KG_PAR_KM_VOITURE  = 0.12   # kg CO2 par km en voiture moyenne (ADEME 2023)
CO2_KG_PAR_VOL_PARIS_NY = 900   # kg CO2 par passager Paris-New York A/R

# Seuils de niveau de risque environnemental (intensité carbone gCO2/t-km)
SEUIL_ROUGE   = 100   # Au-dessus : niveau ROUGE (mauvais)
SEUIL_ORANGE  = 40    # Entre 40 et 100 : niveau ORANGE (moyen)
# En dessous de 40 : niveau VERT (bon)

# Distance maximale pour véhicules électriques (autonomie réelle)
DISTANCE_MAX_EV_KM = 400

# Distance minimale pour recommander le report modal vers le train
DISTANCE_MIN_MODAL_SHIFT_KM = 300


# ─────────────────────────────────────────────────────────────────────────────
# FONCTIONS DE CALCUL
# ─────────────────────────────────────────────────────────────────────────────

def co2_kg(distance_km: float, poids_tonnes: float, mode: str) -> float:
    """
    Calcule les émissions CO2 en kilogrammes pour une route donnée.

    Formule GLEC :
        CO2 (kg) = facteur_emission (gCO2/t-km) × distance (km) × poids (t) / 1000

    Args:
        distance_km   : Distance de la route en kilomètres
        poids_tonnes  : Poids de la marchandise en tonnes
        mode          : Clé du mode de transport (voir FACTEURS_EMISSION)

    Returns:
        Émissions CO2 en kilogrammes (float)

    Raises:
        ValueError : Si le mode de transport est inconnu
    """
    if mode not in FACTEURS_EMISSION:
        modes_disponibles = ", ".join(FACTEURS_EMISSION.keys())
        raise ValueError(
            f"Mode '{mode}' inconnu. Modes disponibles : {modes_disponibles}"
        )

    if distance_km <= 0:
        raise ValueError(f"La distance doit être positive (reçu : {distance_km} km)")

    if poids_tonnes <= 0:
        raise ValueError(f"Le poids doit être positif (reçu : {poids_tonnes} tonnes)")

    # Application de la formule GLEC
    facteur = FACTEURS_EMISSION[mode]  # gCO2e / tonne-km
    co2_grammes = facteur * distance_km * poids_tonnes
    return co2_grammes / 1000.0  # Conversion grammes → kilogrammes


def cout_carbone_eur(co2_kg_val: float) -> float:
    """
    Calcule le coût carbone en euros selon le prix EU ETS.

    Le marché EU ETS (Emissions Trading Scheme) est le marché du carbone
    européen. Prix moyen 2024 : 65€/tonne CO2.

    Args:
        co2_kg_val : Émissions CO2 en kilogrammes

    Returns:
        Coût carbone en euros (float)
    """
    return co2_kg_val * PRIX_CARBONE_EUR_KG


def intensite_carbone(co2_kg_val: float, poids_tonnes: float, distance_km: float) -> float:
    """
    Calcule l'intensité carbone en gCO2e par tonne-km.

    L'intensité carbone permet de comparer des routes de tailles différentes
    sur une base normalisée. C'est le KPI standard GLEC/CSRD.

    Args:
        co2_kg_val   : Émissions CO2 en kilogrammes
        poids_tonnes : Poids de la marchandise en tonnes
        distance_km  : Distance parcourue en kilomètres

    Returns:
        Intensité carbone en gCO2e/tonne-km (float)
        Retourne 0.0 si le calcul est impossible (division par zéro)
    """
    tonne_km = poids_tonnes * distance_km
    if tonne_km <= 0:
        return 0.0
    # Conversion : co2_kg × 1000 → grammes, divisé par tonne-km
    return (co2_kg_val * 1000.0) / tonne_km


def niveau_risque(intensite_gco2_tkm: float) -> str:
    """
    Détermine le niveau de risque environnemental d'une route.

    Basé sur l'intensité carbone (gCO2e/tonne-km) :
    - ROUGE  : > 100 gCO2/t-km (transport très polluant, action urgente)
    - ORANGE : 40-100 gCO2/t-km (amélioration possible)
    - VERT   : < 40 gCO2/t-km (bon niveau, proche des modes propres)

    Args:
        intensite_gco2_tkm : Intensité carbone en gCO2e/t-km

    Returns:
        Chaîne de caractères : 'ROUGE', 'ORANGE' ou 'VERT'
    """
    if intensite_gco2_tkm > SEUIL_ROUGE:
        return "ROUGE"
    elif intensite_gco2_tkm > SEUIL_ORANGE:
        return "ORANGE"
    else:
        return "VERT"


def equivalent_voiture(co2_kg_val: float) -> str:
    """
    Convertit des émissions CO2 en équivalent kilomètres en voiture.

    Rend les chiffres abstraits concrets pour une audience non-technique.
    Basé sur les données ADEME 2023 : voiture moyenne = 120g CO2/km.

    Args:
        co2_kg_val : Émissions CO2 en kilogrammes

    Returns:
        Chaîne de caractères lisible, ex: "= conduire 2 100 km en voiture"
    """
    km_voiture = co2_kg_val / CO2_KG_PAR_KM_VOITURE
    # Formatage avec séparateur de milliers pour la lisibilité
    return f"≈ {km_voiture:,.0f} km en voiture".replace(",", " ")


def get_modes_disponibles() -> list:
    """
    Retourne la liste de tous les modes de transport disponibles.

    Returns:
        Liste des clés de modes de transport
    """
    return list(FACTEURS_EMISSION.keys())


def get_label_mode(mode: str) -> str:
    """
    Retourne le label lisible d'un mode de transport.

    Args:
        mode : Clé du mode de transport

    Returns:
        Label en français, ou le mode original si inconnu
    """
    return LABELS_MODES.get(mode, mode)


def get_emoji_mode(mode: str) -> str:
    """
    Retourne l'emoji associé à un mode de transport.

    Args:
        mode : Clé du mode de transport

    Returns:
        Emoji correspondant, ou '🚛' par défaut
    """
    return EMOJIS_MODES.get(mode, "🚛")


# ─────────────────────────────────────────────────────────────────────────────
# TEST RAPIDE — Exécuté seulement si ce fichier est lancé directement
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("TEST DES FACTEURS D'ÉMISSION GLEC Framework 2023")
    print("=" * 60)

    # Exemple : Casablanca → Marrakech, 8 tonnes, camion diesel grand
    d_km     = 240
    poids_t  = 8
    mode_test = "camion_diesel_grand"

    co2      = co2_kg(d_km, poids_t, mode_test)
    cout     = cout_carbone_eur(co2)
    intensite = intensite_carbone(co2, poids_t, d_km)
    niveau   = niveau_risque(intensite)
    equiv    = equivalent_voiture(co2)

    print(f"\nRoute : Casablanca → Marrakech")
    print(f"Mode  : {get_label_mode(mode_test)} {get_emoji_mode(mode_test)}")
    print(f"Distance : {d_km} km | Poids : {poids_t} t")
    print(f"─" * 40)
    print(f"CO₂ émis      : {co2:.1f} kg CO₂e")
    print(f"Coût carbone  : {cout:.2f} €")
    print(f"Intensité     : {intensite:.1f} gCO₂/t-km")
    print(f"Niveau risque : {niveau}")
    print(f"Équivalent    : {equiv}")
    print("=" * 60)
