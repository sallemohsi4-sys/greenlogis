# 🌿 Green Logistics Optimizer

> **Outil open-source d'optimisation logistique verte et de conformité ESG/CSRD**  
> Projet étudiant — Compétition d'Innovation | Smart Logistique & Supply Chain Management

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red.svg)](https://streamlit.io)
[![GLEC](https://img.shields.io/badge/GLEC_Framework-v3.0-green.svg)](https://smartfreightcentre.org)
[![CSRD](https://img.shields.io/badge/Conformité-CSRD_2024-orange.svg)](https://ec.europa.eu)

---

## 🎯 Problème résolu

Le transport représente **8% des émissions mondiales de CO₂**. La directive **CSRD 2024** oblige désormais les entreprises européennes à déclarer leurs émissions Scope 3 logistiques. Un consultant ESG facture entre **5 000 € et 20 000 €/an** pour ce rapport.

**Green Logistics Optimizer** le fait automatiquement, gratuitement, en **30 secondes**.

---

## ✨ Fonctionnalités

| Module | Description |
|--------|-------------|
| 🔬 **Calcul CO₂ GLEC** | Facteurs d'émission officiels GLEC Framework v3.0 pour 10 modes de transport |
| 📦 **Consolidation** | Détecte les chargements combinables pour réduire le nombre de trajets |
| 🚆 **Report modal** | Identifie les routes camion → train électrique (jusqu'à -96% CO₂) |
| ⚡ **Électrification** | Routes EV-éligibles avec calcul économie carburant |
| 🤖 **IA Claude** | Recommandations personnalisées + copilot questions libres |
| 📄 **Rapport ESG PDF** | Rapport CSRD-conforme de 6 pages généré automatiquement |
| 🗺️ **Carte interactive** | Réseau visualisé avec code couleur ROUGE/ORANGE/VERT |

---

## 📁 Structure du projet

```
green-logistics-optimizer/
├── emission_factors.py     ← Facteurs GLEC officiels (10 modes de transport)
├── calculator.py           ← Calcul CO₂ par route + résumé réseau
├── optimizer.py            ← 3 algorithmes d'optimisation
├── advisor.py              ← Intégration Claude API + fallback hors-ligne
├── esg_report.py           ← Génération PDF ReportLab (6 pages)
├── health_check.py         ← Vérification système avant démo
├── requirements.txt
├── .env                    ← Clés API (ne pas pusher sur GitHub)
├── .gitignore
├── data/
│   └── sample_routes.csv   ← 12 routes démo (Maroc + Europe)
└── dashboard/
    └── app.py              ← Application Streamlit (4 onglets)
```

---

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-username/green-logistics-optimizer.git
cd green-logistics-optimizer
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les clés API

Éditez le fichier `.env` :

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

> 💡 **Sans clé API**, l'application fonctionne en mode hors-ligne avec des recommandations automatiques.  
> Obtenez une clé gratuite sur [console.anthropic.com](https://console.anthropic.com)

### 5. Vérifier l'installation

```bash
python health_check.py
```

Vous devriez voir : `🎉 TOUT EST OK — Prêt pour la démo !`

---

## ▶️ Lancer l'application

```bash
streamlit run dashboard/app.py
```

L'application s'ouvre automatiquement sur `http://localhost:8501`

---

## 📊 Données démo

Le fichier `data/sample_routes.csv` contient **12 routes réalistes** (Maroc + Europe) :

| Trajet | Mode | Niveau |
|--------|------|--------|
| Casablanca → Marrakech | Camion diesel >32t | 🟠 ORANGE |
| Casablanca → Agadir (×2) | Camion diesel >32t | 🔴 ROUGE |
| Tanger → Casablanca | Train électrique | 🟢 VERT |
| Paris → Berlin | **Avion cargo** | 🔴 ROUGE |
| Hambourg → Munich | Camion diesel >32t | 🔴 ROUGE |
| Marseille → Rome | Bateau conteneur | 🟢 VERT |

**Résultats attendus :**
- CO₂ total réseau : ~4 800–5 000 kg CO₂e
- Consolidations détectées : 2+ (Casablanca→Agadir, Paris→Lyon)
- Modal shifts recommandés : 3+ (Hambourg→Munich, Paris→Berlin, Madrid→Barcelone)
- Réduction atteignable : **35–45%**
- Score environnemental initial : **45–55 / 100**

---

## 🔬 Sources des données

| Source | Utilisation |
|--------|-------------|
| [GLEC Framework v3.0](https://www.smartfreightcentre.org/en/our-programs/global-logistics-emissions-council/) | Facteurs d'émission officiels (gCO₂e/t-km) |
| [EU ETS 2024](https://ember-climate.org/data/data-tools/carbon-price-viewer/) | Prix du carbone (65 €/tonne CO₂) |
| [CSRD / ESRS E1](https://ec.europa.eu/sustainability-reporting) | Standard de reporting ESG |
| [ADEME 2023](https://www.ademe.fr) | Émissions voiture (120g CO₂/km) |
| [Anthropic Claude](https://anthropic.com) | IA générative pour recommandations |

---

## 🏗️ Architecture

```
CSV Input
    ↓
calculator.py (GLEC formulas)
    ↓
optimizer.py (3 algorithms)
    ├── Consolidation algorithm
    ├── Modal shift algorithm  
    └── EV routing algorithm
    ↓
advisor.py (Claude API)
    ↓
esg_report.py (ReportLab PDF)
    ↓
dashboard/app.py (Streamlit UI)
```

---

## 🌐 Déploiement Streamlit Cloud

1. Pousser le code sur GitHub (sans `.env`)
2. Aller sur [share.streamlit.io](https://share.streamlit.io)
3. Connecter le dépôt GitHub
4. Ajouter `ANTHROPIC_API_KEY` dans les secrets Streamlit
5. Déployer → URL publique gratuite

**Application live :** `https://votre-app.streamlit.app` *(à compléter après déploiement)*

---

## 👤 Auteur

**[Votre Nom]**  
Étudiant 2ème année — Ingénierie Smart Logistique & Supply Chain Management  
École : [Votre École]  
Compétition : Innovation Étudiante 2024  
Contact : [votre.email@ecole.ma]

---

## 📄 Licence

MIT License — Projet open-source étudiant.  
Utilisation libre pour des fins éducatives et non-commerciales.
