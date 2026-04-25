"""
advisor.py — Intégration Claude API pour recommandations ESG
=============================================================
Ce module utilise l'API Anthropic (Claude claude-sonnet-4-20250514) pour :
  1. Générer des recommandations logistiques vertes personnalisées
  2. Répondre aux questions libres de l'utilisateur (copilot IA)
  3. Rédiger la section "Émissions Scope 3" du rapport ESG annuel
"""

import os
import json
import anthropic
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION DU CLIENT CLAUDE
# ─────────────────────────────────────────────────────────────────────────────

# Modèle Claude à utiliser (claude-sonnet-4-20250514 = bon équilibre qualité/coût)
MODELE_CLAUDE = "claude-sonnet-4-20250514"
MAX_TOKENS    = 600   # Réponses concises et précises

# Message système — Identité du consultant virtuel
SYSTEM_PROMPT = """Tu es un consultant senior en logistique verte et ESG (Environmental, Social, Governance) 
avec 15 ans d'expérience dans l'optimisation des chaînes d'approvisionnement durables.
Tu maîtrises parfaitement :
- Le GLEC Framework (Global Logistics Emissions Council)
- La directive européenne CSRD (Corporate Sustainability Reporting Directive)
- Les marchés carbone EU ETS et les prix du CO₂
- Les stratégies de décarbonation logistique (Scope 3)
- Le report modal, la consolidation de chargements, l'électrification des flottes

Tes recommandations sont TOUJOURS :
✅ Concrètes et actionnables (pas de généralités)
✅ Chiffrées avec des KPIs précis (%, kg CO₂, €)
✅ Priorisées par impact environnemental et ROI
✅ Alignées avec les objectifs Paris Agreement (-55% CO₂ d'ici 2030)

Réponds TOUJOURS en français. Sois direct et professionnel. Maximum 400 mots par réponse."""


def _creer_client() -> Optional[anthropic.Anthropic]:
    """
    Crée et retourne un client Anthropic.

    Lit la clé API depuis la variable d'environnement ANTHROPIC_API_KEY
    ou depuis le fichier .env dans le répertoire courant.

    Returns:
        Client Anthropic si la clé est disponible, None sinon
    """
    # Essai 1 : variable d'environnement directe
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Essai 2 : lecture du fichier .env si la clé n'est pas en env
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        except ImportError:
            pass

    if not api_key or api_key == "your_key_here":
        return None

    return anthropic.Anthropic(api_key=api_key)


def generer_recommandations(
    df_analyse,
    consolidations: list,
    modal_shifts: list,
    synthese: dict = None,
) -> str:
    """
    Génère des recommandations logistiques vertes personnalisées avec Claude.

    Analyse le réseau de livraisons et les opportunités d'optimisation pour
    produire un plan d'action concret et chiffré.

    Args:
        df_analyse      : DataFrame enrichi (produit par analyser_reseau)
        consolidations  : Liste des opportunités de consolidation
        modal_shifts    : Liste des opportunités de report modal
        synthese        : Dictionnaire de synthèse (optionnel, produit par synthese_optimisations)

    Returns:
        Texte des recommandations en français (str)
        Message d'erreur explicite si l'API est indisponible
    """
    client = _creer_client()

    if client is None:
        return _recommandations_sans_ia(df_analyse, consolidations, modal_shifts, synthese)

    # ── Construction du résumé pour le prompt
    try:
        nb_routes      = len(df_analyse)
        co2_total      = df_analyse["co2_kg"].sum()
        intensite_moy  = df_analyse["intensite_gco2"].mean() if "intensite_gco2" in df_analyse.columns else 0
        nb_rouge       = int((df_analyse["niveau_risque"] == "ROUGE").sum()) if "niveau_risque" in df_analyse.columns else 0
        nb_consolid    = len(consolidations)
        nb_modal       = len(modal_shifts)
        co2_econom     = synthese.get("co2_total_eco", 0) if synthese else 0
        pct_reduc      = synthese.get("pct_reduction_total", 0) if synthese else 0

        # Top 3 routes polluantes
        top_routes = ""
        if "co2_kg" in df_analyse.columns:
            top = df_analyse.nlargest(3, "co2_kg")[
                ["origine", "destination", "mode", "co2_kg", "niveau_risque"]
            ]
            top_routes = top.to_string(index=False)

        # Résumé consolidations
        resumes_consolid = ""
        for c in consolidations[:3]:
            resumes_consolid += (
                f"  • {c['origines']} → {c['destinations']} : "
                f"-{c['co2_economise']:.1f} kg CO₂ ({c['pct_reduction']:.0f}%)\n"
            )

        # Résumé modal shifts
        resumes_modal = ""
        for ms in modal_shifts[:3]:
            opt = ms["meilleure_option"]
            resumes_modal += (
                f"  • {ms['origine']} → {ms['destination']} "
                f"({ms['mode_actuel']} → {opt['mode_cible']}) : "
                f"-{opt['co2_economise']:.1f} kg CO₂ ({opt['pct_reduction']:.0f}%)\n"
            )

        prompt_utilisateur = f"""Analyse ce réseau logistique et donne tes recommandations :

RÉSEAU ACTUEL :
- {nb_routes} routes de livraison
- CO₂ total : {co2_total:.1f} kg CO₂e
- Intensité moyenne : {intensite_moy:.1f} gCO₂/t-km
- Routes niveau ROUGE (urgence) : {nb_rouge}

TOP 3 ROUTES LES PLUS POLLUANTES :
{top_routes}

OPPORTUNITÉS IDENTIFIÉES PAR L'ALGORITHME :
Consolidations possibles ({nb_consolid}) :
{resumes_consolid if resumes_consolid else "  Aucune détectée"}

Reports modaux possibles ({nb_modal}) :
{resumes_modal if resumes_modal else "  Aucun détecté"}

POTENTIEL TOTAL : -{pct_reduc:.1f}% CO₂ ({co2_econom:.1f} kg évitables)

Donne-moi un plan d'action en 3 étapes, chiffré, priorisé par impact et faisabilité.
"""
    except Exception as e:
        return _recommandations_sans_ia(df_analyse, consolidations, modal_shifts, synthese)

    try:
        response = client.messages.create(
            model=MODELE_CLAUDE,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt_utilisateur}]
        )
        return response.content[0].text

    except anthropic.AuthenticationError:
        return (
            "⚠️ **Clé API invalide** — Vérifiez votre clé ANTHROPIC_API_KEY dans le fichier `.env`.\n\n"
            + _recommandations_sans_ia(df_analyse, consolidations, modal_shifts, synthese)
        )
    except anthropic.RateLimitError:
        return (
            "⚠️ **Limite API atteinte** — Réessayez dans quelques secondes.\n\n"
            + _recommandations_sans_ia(df_analyse, consolidations, modal_shifts, synthese)
        )
    except Exception as e:
        return (
            f"⚠️ **Erreur API** : {str(e)}\n\n"
            + _recommandations_sans_ia(df_analyse, consolidations, modal_shifts, synthese)
        )


def repondre_question(question: str, contexte_reseau: dict) -> str:
    """
    Répond à une question libre de l'utilisateur sur son réseau logistique.

    Sert de copilot IA dans l'onglet "IA Conseiller" du dashboard.

    Args:
        question        : Question posée par l'utilisateur (texte libre)
        contexte_reseau : Dictionnaire résumé du réseau (produit par resume_reseau)

    Returns:
        Réponse de Claude en français (str)
        Réponse générique si l'API est indisponible
    """
    client = _creer_client()

    if not question or not question.strip():
        return "❓ Veuillez poser une question pour obtenir une réponse."

    # Construction du contexte réseau pour le prompt
    contexte_str = f"""Contexte du réseau logistique analysé :
- CO₂ total : {contexte_reseau.get('total_co2_kg', 'N/A')} kg
- Score environnemental : {contexte_reseau.get('score_environnemental', 'N/A')}/100
- Intensité carbone moyenne : {contexte_reseau.get('intensite_moyenne', 'N/A')} gCO₂/t-km
- Benchmark industrie : {contexte_reseau.get('benchmark_industrie', 85)} gCO₂/t-km
- Routes ROUGE : {contexte_reseau.get('nb_rouge', 0)}
- Mode dominant : {contexte_reseau.get('mode_le_plus_utilise', 'N/A')}
- Réduction potentielle : {contexte_reseau.get('pct_reduction_total', 'voir optimisations')}"""

    if client is None:
        return _reponse_generique(question)

    try:
        prompt = f"{contexte_str}\n\nQuestion de l'utilisateur : {question}"

        response = client.messages.create(
            model=MODELE_CLAUDE,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    except anthropic.AuthenticationError:
        return "⚠️ Clé API invalide. Configurez ANTHROPIC_API_KEY dans `.env`.\n\n" + _reponse_generique(question)
    except Exception as e:
        return f"⚠️ Erreur API ({e}).\n\n" + _reponse_generique(question)


def rediger_section_esg(resume_reseau: dict, synthese_optim: dict = None) -> str:
    """
    Rédige la section "Émissions Scope 3 — Logistique" du rapport ESG annuel.

    Ce texte est directement utilisable dans un rapport d'entreprise
    conforme à la directive CSRD 2024 (Corporate Sustainability Reporting).

    Args:
        resume_reseau   : Dictionnaire produit par resume_reseau()
        synthese_optim  : Dictionnaire de synthèse des optimisations (optionnel)

    Returns:
        Texte professionnel de 300-400 mots pour le rapport annuel ESG
    """
    client = _creer_client()

    co2_kg     = resume_reseau.get("total_co2_kg", 0)
    co2_t      = resume_reseau.get("total_co2_tonnes", co2_kg / 1000)
    score      = resume_reseau.get("score_environnemental", 50)
    intensite  = resume_reseau.get("intensite_moyenne", 0)
    periode    = resume_reseau.get("periode", "2024")
    pct_reduc  = synthese_optim.get("pct_reduction_total", 0) if synthese_optim else 0
    economie   = synthese_optim.get("co2_total_eco", 0) if synthese_optim else 0

    if client is None:
        return _section_esg_statique(resume_reseau, synthese_optim)

    prompt = f"""Rédige la section "Émissions de Scope 3 — Transport et Logistique" 
d'un rapport ESG annuel conforme à la directive CSRD 2024, avec ces données :

Période : {periode}
CO₂ total transport : {co2_t:.3f} tonnes CO₂e
Intensité carbone : {intensite:.1f} gCO₂/t-km
Score environnemental : {score}/100 (méthode GLEC Framework 2023)
Potentiel de réduction identifié : -{pct_reduc:.0f}% ({economie:.0f} kg CO₂)

Le texte doit :
1. Mentionner explicitement la conformité CSRD et la méthode GLEC Framework
2. Présenter les données avec les unités correctes (tCO₂e, gCO₂/t-km)
3. Décrire le plan d'action pour atteindre -30% d'ici 12 mois
4. Être professionnel et prêt à copier dans un rapport annuel
5. Faire environ 350 mots
"""

    try:
        response = client.messages.create(
            model=MODELE_CLAUDE,
            max_tokens=800,  # Section plus longue pour le rapport officiel
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    except Exception as e:
        return f"⚠️ Erreur API ({e}).\n\n" + _section_esg_statique(resume_reseau, synthese_optim)


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK — Recommandations sans API (mode hors-ligne)
# ─────────────────────────────────────────────────────────────────────────────

def _recommandations_sans_ia(df_analyse, consolidations, modal_shifts, synthese) -> str:
    """
    Génère des recommandations automatiques sans l'API Claude.
    Utilisé en mode démo ou si la clé API n'est pas configurée.
    """
    lines = ["## 🌿 Plan d'action — Optimisation logistique verte\n"]
    lines.append("*Recommandations générées automatiquement (mode hors-ligne)*\n")

    if synthese:
        pct = synthese.get("pct_reduction_total", 0)
        eco = synthese.get("co2_total_eco", 0)
        eur = synthese.get("economie_eur_totale", 0)
        lines.append(f"**Potentiel identifié : -{pct:.0f}% CO₂** "
                     f"({eco:,.0f} kg CO₂ évitables, économie {eur:.0f}€)\n")

    lines.append("\n### 🚀 Action 1 — Consolidation des chargements (Priorité HAUTE)")
    if consolidations:
        c = consolidations[0]
        lines.append(
            f"Combiner les livraisons **{c['origines']} → {c['destinations']}** "
            f"dans un seul camion. Économie immédiate : **{c['co2_economise']:.0f} kg CO₂** "
            f"({c['pct_reduction']:.0f}% de réduction) et **{c['economie_eur']:.1f}€** "
            f"d'économies carbone. Taux de remplissage : {c['taux_remplissage']:.0f}%."
        )
    else:
        lines.append("Aucune opportunité de consolidation détectée sur ce réseau.")

    lines.append("\n### 🚆 Action 2 — Report modal vers le train (Priorité HAUTE)")
    if modal_shifts:
        ms = modal_shifts[0]
        opt = ms["meilleure_option"]
        lines.append(
            f"Transférer la route **{ms['origine']} → {ms['destination']}** "
            f"du camion diesel vers **{opt['mode_cible']}**. "
            f"Réduction : **-{opt['pct_reduction']:.0f}% CO₂** "
            f"({opt['co2_economise']:.0f} kg évités). {opt.get('note', '')}"
        )
    else:
        lines.append("Aucun report modal recommandé (routes trop courtes ou déjà optimisées).")

    lines.append("\n### ⚡ Action 3 — Électrification de la flotte (Priorité MOYENNE)")
    if "co2_ev_eco" in (synthese or {}):
        ev_eco = synthese["co2_ev_eco"]
        lines.append(
            f"Les routes courtes (<400 km) peuvent être électrifiées. "
            f"Économie potentielle : **{ev_eco:.0f} kg CO₂**. "
            f"Coût initial : investissement dans des véhicules électriques "
            f"compensé par les économies de carburant (~60% moins cher que le diesel)."
        )

    lines.append(
        "\n---\n"
        "**⚙️ Pour activer les recommandations IA personnalisées**, "
        "ajoutez votre clé `ANTHROPIC_API_KEY` dans le fichier `.env`."
    )
    return "\n".join(lines)


def _reponse_generique(question: str) -> str:
    """
    Réponse générique si l'API Claude est indisponible.
    """
    q = question.lower()

    if "priorité" in q or "priorite" in q or "commencer" in q:
        return (
            "**Vos 3 priorités vertes :**\n\n"
            "1. 🚛 **Consolidation** — Combinez les livraisons même origine/destination "
            "(gain immédiat de 15-30% CO₂ sans investissement)\n"
            "2. 🚆 **Report modal** — Basculez les longues distances (>300 km) "
            "vers le train électrique (-80% CO₂)\n"
            "3. ⚡ **Électrification** — Remplacez les camions diesel sur les "
            "routes < 400 km par des véhicules électriques (-52% CO₂)\n\n"
            "*Activez la clé Claude API pour des recommandations personnalisées.*"
        )
    elif "30%" in q or "réduire" in q or "reduire" in q:
        return (
            "**Plan -30% CO₂ en 6 mois :**\n\n"
            "- **Mois 1-2** : Consolidation des chargements → -10 à 15%\n"
            "- **Mois 3-4** : Report modal longues distances → -10 à 20%\n"
            "- **Mois 5-6** : Pilote camions électriques → -5 à 10%\n\n"
            "Résultat cible : -35% CO₂, aligné sur Paris Agreement."
        )
    elif "mode" in q or "transport" in q or "éliminer" in q:
        return (
            "**Mode à réduire en priorité : l'avion cargo** ✈️\n\n"
            "L'avion émet **602 gCO₂/t-km**, soit 6× plus que le camion diesel. "
            "Remplacez systématiquement par le fret ferroviaire pour les envois "
            "non-urgents. Si vous n'avez pas d'avion, ciblez les petits camions diesel "
            "(200 gCO₂/t-km) sur courtes distances — remplacez par véhicule électrique."
        )
    else:
        return (
            "**Réponse automatique** (API Claude non configurée)\n\n"
            "Pour des réponses personnalisées à votre question, "
            "configurez votre clé `ANTHROPIC_API_KEY` dans le fichier `.env`.\n\n"
            "En attendant, consultez :\n"
            "- L'onglet **Optimisations** pour les actions concrètes\n"
            "- L'onglet **Rapport ESG** pour la conformité CSRD\n"
            "- Le [GLEC Framework](https://www.smartfreightcentre.org) pour les méthodologies"
        )


def _section_esg_statique(resume: dict, synthese: dict = None) -> str:
    """
    Section ESG pré-rédigée sans API Claude.
    """
    co2_t = resume.get("total_co2_tonnes", 0)
    score = resume.get("score_environnemental", 50)
    intensite = resume.get("intensite_moyenne", 0)
    periode = resume.get("periode", "Exercice 2024")
    pct = synthese.get("pct_reduction_total", 0) if synthese else 0

    return f"""## Émissions de Scope 3 — Transport et Logistique amont/aval

*Période de reporting : {periode}*

### Méthodologie

Les émissions liées au transport de marchandises ont été calculées conformément 
au **GLEC Framework v3.0** (Global Logistics Emissions Council, 2023), référence 
mondiale pour la comptabilisation des émissions logistiques Scope 3. 
Cette approche est alignée avec les exigences de la directive européenne **CSRD** 
(Corporate Sustainability Reporting Directive, 2024).

### Résultats

Pour la période {periode}, les émissions totales de transport s'élèvent à 
**{co2_t:.3f} tCO₂e**, avec une intensité carbone de **{intensite:.1f} gCO₂e/tonne-km**.

Notre score environnemental calculé selon la méthode GLEC est de **{score}/100**.

### Plan de réduction

Notre analyse algorithmique identifie un potentiel de réduction de **{pct:.0f}%** 
grâce à trois leviers :
1. **Consolidation des chargements** — Mutualisation des camions entre envois compatibles
2. **Report modal** — Basculement vers le transport ferroviaire sur les longues distances
3. **Électrification progressive** — Remplacement des véhicules diesel sur les routes < 400 km

**Objectif : -30% d'émissions de transport d'ici 12 mois**, aligné sur l'Accord de Paris 
et la trajectoire Net Zéro 2050 de l'UE.

### Conformité CSRD

Ce rapport respecte les exigences de l'European Sustainability Reporting Standard 
**ESRS E1** (changement climatique) et notamment le point E1-6 relatif aux émissions 
brutes de GES de Scope 3.
"""


# ─────────────────────────────────────────────────────────────────────────────
# TEST RAPIDE
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("TEST — Module advisor.py")
    print("=" * 60)

    client = _creer_client()
    if client:
        print("✅ Clé API Claude configurée — mode IA activé")
    else:
        print("⚠️  Clé API non configurée — mode hors-ligne (fallback automatique)")

    # Test de la réponse générique
    rep = _reponse_generique("Quelles sont mes 3 priorités vertes ?")
    print(f"\n📝 Réponse générique :\n{rep[:300]}...")
