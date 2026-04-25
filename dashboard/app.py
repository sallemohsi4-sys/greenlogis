"""
dashboard/app.py — Application Streamlit principale
Green Logistics Optimizer
Usage : streamlit run dashboard/app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from emission_factors import get_label_mode, get_emoji_mode, FACTEURS_EMISSION
from calculator import analyser_reseau, resume_reseau, top_routes_polluantes
from optimizer import optimiser_reseau
from advisor import generer_recommandations, repondre_question, rediger_section_esg
from esg_report import generer_rapport_pdf

# ── Configuration de la page
st.set_page_config(
    page_title="Green Logistics Optimizer",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personnalisé
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #0f1117; }
.stMetric { background: linear-gradient(135deg,#1B4332,#2D6A4F); border-radius:12px;
            padding:16px; border:1px solid #52B788; }
.stMetric label { color:#B7E4C7 !important; font-size:0.8rem !important; }
.stMetric [data-testid="stMetricValue"] { color:#fff !important; font-size:1.8rem !important; font-weight:800; }
.kpi-card { background:linear-gradient(135deg,#1B4332,#2D6A4F); border-radius:14px;
            padding:20px; text-align:center; border:1px solid #40916C; margin:4px; }
.kpi-val  { font-size:2rem; font-weight:800; color:#B7E4C7; }
.kpi-lbl  { font-size:0.78rem; color:#95D5B2; margin-top:4px; }
.badge-rouge  { background:#C0392B; color:#fff; padding:3px 10px; border-radius:20px;
                font-size:0.75rem; font-weight:600; }
.badge-orange { background:#E67E22; color:#fff; padding:3px 10px; border-radius:20px;
                font-size:0.75rem; font-weight:600; }
.badge-vert   { background:#27AE60; color:#fff; padding:3px 10px; border-radius:20px;
                font-size:0.75rem; font-weight:600; }
.alert-box { background:linear-gradient(135deg,#1a3a2a,#0d2b1e); border-left:4px solid #52B788;
             border-radius:8px; padding:16px; margin:8px 0; color:#B7E4C7; }
div.stButton > button { background:linear-gradient(135deg,#2D6A4F,#40916C); color:#fff;
                        border:none; border-radius:8px; font-weight:600; padding:8px 20px;
                        transition:all 0.2s; }
div.stButton > button:hover { background:linear-gradient(135deg,#40916C,#52B788);
                               transform:translateY(-1px); box-shadow:0 4px 12px #52B78850; }
.sidebar-logo { font-size:1.8rem; font-weight:800; color:#52B788; text-align:center;
                padding:10px 0; border-bottom:1px solid #2D6A4F; margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────
# CHARGEMENT ET CACHE DES DONNÉES
# ────────────────────────────────────────────────────────────────
CHEMIN_DEMO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "sample_routes.csv"
)

@st.cache_data(show_spinner="🔄 Analyse du réseau en cours...")
def charger_et_analyser(source):
    """Charge, analyse et optimise le réseau logistique (mis en cache)."""
    df  = analyser_reseau(source)
    res = resume_reseau(df)
    opt = optimiser_reseau(df)
    return df, res, opt

def badge_html(niveau):
    return f'<span class="badge-{niveau.lower()}">{niveau}</span>'

# ────────────────────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🌿 GreenLogistics<br><span style="font-size:0.65rem;color:#95D5B2;font-weight:400">Optimizer v1.0</span></div>', unsafe_allow_html=True)

    st.markdown(f"🕐 **{datetime.now().strftime('%d/%m/%Y %H:%M')}**")
    st.markdown("---")

    # Upload CSV ou démo
    st.markdown("### 📂 Source de données")
    mode_source = st.radio("", ["📊 Données démo", "📁 Importer CSV"], label_visibility="collapsed")

    uploaded = None
    if mode_source == "📁 Importer CSV":
        uploaded = st.file_uploader(
            "Votre fichier CSV", type="csv",
            help="Colonnes requises : origine, destination, mode, distance_km, poids_tonnes, date"
        )

    if st.button("🔄 Actualiser les données"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Paramètres rapport")
    nom_entreprise = st.text_input("Nom entreprise", "Mon Entreprise")
    periode_rapport = st.text_input("Période", datetime.now().strftime("%B %Y"))

    st.markdown("---")
    st.markdown("### 📚 Sources")
    st.markdown("""
- [GLEC Framework v3.0](https://www.smartfreightcentre.org)
- [Directive CSRD 2024](https://ec.europa.eu)
- [EU ETS Prix carbone](https://ember-climate.org)
- [Claude AI — Anthropic](https://anthropic.com)
""")
    st.markdown("---")
    st.caption("🎓 Projet étudiant — Compétition Innovation\nSmart Logistique & Supply Chain")

# ────────────────────────────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ────────────────────────────────────────────────────────────────
try:
    if uploaded is not None:
        source = uploaded
    else:
        source = CHEMIN_DEMO

    df, res, opt = charger_et_analyser(source)
    synthese = opt["synthese"]
    consolidations = opt["consolidations"]
    modal_shifts   = opt["modal_shifts"]
    ev_routes      = opt["ev_routes"]
    DATA_OK = True

except Exception as e:
    st.error(f"❌ Erreur de chargement : {e}")
    st.info("💡 Vérifiez le format du CSV ou utilisez les données démo.")
    DATA_OK = False
    st.stop()

# ────────────────────────────────────────────────────────────────
# ONGLETS PRINCIPAUX
# ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Tableau de bord",
    "⚡ Optimisations",
    "🤖 IA Conseiller",
    "📄 Rapport ESG"
])

# ════════════════════════════════════════════════════════════════
# ONGLET 1 — TABLEAU DE BORD
# ════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("## 🌍 Tableau de bord — Réseau logistique")

    # ── KPIs Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🌫️ CO₂ Total Réseau", f"{res['total_co2_kg']:,.0f} kg",
                  delta=f"Scope 3 logistique", delta_color="off")
    with c2:
        st.metric("💰 Coût Carbone EU ETS", f"{res['total_cout_eur']:,.2f} €",
                  delta="65 €/tonne CO₂", delta_color="off")
    with c3:
        score = res['score_environnemental']
        couleur_delta = "normal" if score >= 60 else "inverse"
        st.metric("🌿 Score Environnemental", f"{score:.0f} / 100",
                  delta=f"Benchmark : {res['benchmark_industrie']} gCO₂/t-km", delta_color="off")
    with c4:
        st.metric("⚡ Économies Potentielles", f"{synthese['co2_total_eco']:,.0f} kg CO₂",
                  delta=f"-{synthese['pct_reduction_total']:.0f}% atteignable", delta_color="normal")

    st.markdown("---")

    # ── Carte + Feed alertes
    col_map, col_feed = st.columns([3, 2])

    with col_map:
        st.markdown("### 🗺️ Carte du réseau logistique")
        try:
            import folium
            from streamlit_folium import st_folium

            # Coordonnées approximatives des villes
            COORDS = {
                "casablanca": (33.5731, -7.5898), "marrakech": (31.6295, -7.9811),
                "agadir": (30.4278, -9.5981), "fes": (34.0181, -5.0078),
                "tanger": (35.7595, -5.8340), "rabat": (34.0209, -6.8416),
                "paris": (48.8566, 2.3522), "lyon": (45.7640, 4.8357),
                "hambourg": (53.5488, 9.9872), "munich": (48.1351, 11.5820),
                "berlin": (52.5200, 13.4050), "marseille": (43.2965, 5.3698),
                "rome": (41.9028, 12.4964), "madrid": (40.4168, -3.7038),
                "barcelone": (41.3851, 2.1734),
            }

            # Centre de la carte
            m = folium.Map(location=[38, 5], zoom_start=4,
                           tiles="CartoDB dark_matter")

            couleurs_mode = {
                "camion_diesel_grand": "red", "camion_diesel_moyen": "orange",
                "camion_diesel_petit": "orange", "camion_electrique": "green",
                "train_electrique": "blue", "train_electrique_france": "blue",
                "train_diesel": "cadetblue", "bateau_conteneur": "purple",
                "bateau_vrac": "purple", "avion_fret": "darkred",
            }

            for _, row in df.iterrows():
                orig_k = row["origine"].lower()
                dest_k = row["destination"].lower()
                c_orig = COORDS.get(orig_k)
                c_dest = COORDS.get(dest_k)

                if not c_orig or not c_dest:
                    continue

                # Ligne de route
                couleur = couleurs_mode.get(row["mode"], "gray")
                folium.PolyLine(
                    [c_orig, c_dest],
                    color=couleur, weight=2.5, opacity=0.75,
                    tooltip=f"{row['origine']} → {row['destination']} | "
                            f"{row.get('co2_kg',0):.1f} kg CO₂ | "
                            f"{row.get('niveau_risque','?')}"
                ).add_to(m)

                # Marqueurs
                for coord, nom in [(c_orig, row["origine"]), (c_dest, row["destination"])]:
                    folium.CircleMarker(
                        coord, radius=5, color="white", fill=True,
                        fill_color="#52B788", fill_opacity=0.9,
                        popup=folium.Popup(nom, parse_html=True)
                    ).add_to(m)

            st_folium(m, width=700, height=400)

        except ImportError:
            st.info("📦 Installez streamlit-folium pour la carte interactive : `pip install streamlit-folium`")
            # Tableau de substitution
            st.dataframe(
                df[["origine","destination","mode","distance_km","co2_kg","niveau_risque"]],
                use_container_width=True
            )

    with col_feed:
        st.markdown("### 🚨 Alertes — Routes prioritaires")
        top5 = top_routes_polluantes(df, 5)
        for i, (_, row) in enumerate(top5.iterrows(), 1):
            niveau = row.get("niveau_risque", "ORANGE")
            emoji_n = {"ROUGE": "🔴", "ORANGE": "🟠", "VERT": "🟢"}.get(niveau, "⚪")
            st.markdown(f"""
<div class="alert-box">
<b>{i}. {emoji_n} {row['origine']} → {row['destination']}</b><br>
{get_emoji_mode(row['mode'])} {get_label_mode(row['mode'])}<br>
<b style="color:#52B788">{row.get('co2_kg',0):,.1f} kg CO₂</b>
 · {row.get('intensite_gco2',0):.0f} gCO₂/t-km
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Graphiques
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### 🥧 Répartition CO₂ par mode")
        rep = res.get("repartition_co2_mode", {})
        if rep:
            labels = [f"{v.get('emoji','')} {k}" for k, v in rep.items()]
            values = [v["co2_kg"] for v in rep.values()]
            fig_donut = go.Figure(go.Pie(
                labels=labels, values=values, hole=0.55,
                marker=dict(colors=["#52B788","#40916C","#2D6A4F","#E67E22","#C0392B","#8E44AD"]),
                textfont=dict(color="white"),
            ))
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", legend=dict(font=dict(color="white")),
                margin=dict(t=20, b=20, l=20, r=20), height=300,
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    with col_g2:
        st.markdown("### 📊 CO₂ par route")
        if "co2_kg" in df.columns:
            df_plot = df.copy()
            df_plot["label_route"] = df_plot["origine"].str[:8] + "→" + df_plot["destination"].str[:8]
            fig_bar = px.bar(
                df_plot.sort_values("co2_kg", ascending=False),
                x="label_route", y="co2_kg",
                color="niveau_risque",
                color_discrete_map={"ROUGE":"#C0392B","ORANGE":"#E67E22","VERT":"#27AE60"},
                labels={"co2_kg": "CO₂ (kg)", "label_route": "Route"},
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", showlegend=True,
                xaxis=dict(tickangle=-35, gridcolor="#1B4332"),
                yaxis=dict(gridcolor="#1B4332"),
                margin=dict(t=20, b=60), height=300,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # ── Tableau complet
    st.markdown("### 📋 Détail complet du réseau")
    df_display = df[["origine","destination","label_mode","distance_km","poids_tonnes",
                     "co2_kg","cout_eur","intensite_gco2","niveau_risque","equivalent_voit"]].copy()
    df_display.columns = ["Origine","Destination","Mode","Dist. (km)","Poids (t)",
                          "CO₂ (kg)","Coût (€)","Intensité","Niveau","Équiv. voiture"]
    st.dataframe(df_display, use_container_width=True, height=300)


# ════════════════════════════════════════════════════════════════
# ONGLET 2 — OPTIMISATIONS
# ════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## ⚡ Optimisations — Réduction CO₂")

    # Compteur économies
    if "eco_appliquees_co2" not in st.session_state:
        st.session_state.eco_appliquees_co2 = 0.0
        st.session_state.eco_appliquees_eur = 0.0

    c_eco1, c_eco2, c_eco3 = st.columns(3)
    with c_eco1:
        st.metric("🎯 Potentiel total", f"{synthese['co2_total_eco']:,.0f} kg CO₂",
                  f"-{synthese['pct_reduction_total']:.0f}%", delta_color="normal")
    with c_eco2:
        st.metric("✅ Économies appliquées", f"{st.session_state.eco_appliquees_co2:,.0f} kg CO₂")
    with c_eco3:
        st.metric("💰 Économies EU ETS", f"{st.session_state.eco_appliquees_eur:,.2f} €")

    st.markdown("---")

    # ── Section consolidations
    st.markdown("### 📦 Consolidation de chargements")
    if consolidations:
        for c in consolidations:
            with st.expander(
                f"{'🟢' if c['faisabilite']=='FACILE' else '🟠' if c['faisabilite']=='MOYEN' else '🔴'} "
                f"{c['id']} — {c['origines']} → {c['destinations']} "
                f"| **-{c['co2_economise']:.0f} kg CO₂** (-{c['pct_reduction']:.0f}%)"
            ):
                cols = st.columns(3)
                cols[0].metric("CO₂ économisé", f"{c['co2_economise']:.1f} kg")
                cols[1].metric("Économie €", f"{c['economie_eur']:.2f} €")
                cols[2].metric("Taux remplissage", f"{c['taux_remplissage']:.0f}%")

                st.markdown(f"**Route 1** : {c['route_1']['date']} — {c['route_1']['poids']}t — {c['route_1']['co2_kg']} kg CO₂")
                st.markdown(f"**Route 2** : {c['route_2']['date']} — {c['route_2']['poids']}t — {c['route_2']['co2_kg']} kg CO₂")
                st.markdown(f"**Poids combiné** : {c['poids_combine']} t / {24} t max")

                if c["contraintes"]:
                    for ct in c["contraintes"]:
                        st.warning(f"⚠️ {ct}")

                if st.button(f"✅ Appliquer {c['id']}", key=f"btn_c_{c['id']}"):
                    st.session_state.eco_appliquees_co2 += c["co2_economise"]
                    st.session_state.eco_appliquees_eur += c["economie_eur"]
                    st.success(f"✅ {c['co2_economise']:.0f} kg CO₂ économisés !")
                    st.rerun()
    else:
        st.info("Aucune opportunité de consolidation détectée sur ce réseau.")

    st.markdown("---")

    # ── Section modal shifts
    st.markdown("### 🚆 Report modal (camion → train / électrique)")
    if modal_shifts:
        for ms in modal_shifts:
            opt = ms["meilleure_option"]
            with st.expander(
                f"🚆 {ms['id']} — {ms['origine']} → {ms['destination']} "
                f"| **-{opt['co2_economise']:.0f} kg CO₂** (-{opt['pct_reduction']:.0f}%)"
            ):
                cols = st.columns(4)
                cols[0].metric("Mode actuel", ms["mode_actuel"])
                cols[1].metric("Meilleure option", opt["mode_cible"])
                cols[2].metric("CO₂ économisé", f"{opt['co2_economise']:.1f} kg")
                cols[3].metric("Économie €", f"{opt['economie_eur']:.2f} €")

                st.caption(f"📏 {ms['distance_km']} km · {ms['poids_tonnes']} t · {opt['delai_supp_pct']}")
                if opt.get("note"):
                    st.info(f"💡 {opt['note']}")

                # Toutes les alternatives
                if len(ms["alternatives"]) > 1:
                    st.markdown("**Autres alternatives :**")
                    for alt in ms["alternatives"]:
                        st.caption(f"• {alt['mode_cible']} : -{alt['co2_economise']:.0f} kg CO₂ ({alt['pct_reduction']:.0f}%)")

                if st.button(f"✅ Appliquer {ms['id']}", key=f"btn_m_{ms['id']}"):
                    st.session_state.eco_appliquees_co2 += opt["co2_economise"]
                    st.session_state.eco_appliquees_eur += opt["economie_eur"]
                    st.success(f"✅ {opt['co2_economise']:.0f} kg CO₂ économisés !")
                    st.rerun()
    else:
        st.info("Aucun report modal recommandé.")

    st.markdown("---")

    # ── EV Routes
    st.markdown("### ⚡ Routes EV-éligibles (électrification)")
    if ev_routes:
        rows_ev = []
        for ev in ev_routes:
            rows_ev.append({
                "ID": ev["id"],
                "Trajet": f"{ev['origine']} → {ev['destination']}",
                "Distance": f"{ev['distance_km']} km",
                "Mode actuel": ev["mode_actuel"],
                "CO₂ économisé": f"{ev['co2_economise']:.0f} kg",
                "Réduction": f"-{ev['pct_reduction']:.0f}%",
                "Éco. carburant": f"{ev['economie_carburant_eur']:.0f} €/trajet",
            })
        st.dataframe(pd.DataFrame(rows_ev), use_container_width=True)
    else:
        st.info("Aucune route EV-éligible (toutes > 400 km).")

# ════════════════════════════════════════════════════════════════
# ONGLET 3 — IA CONSEILLER
# ════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("## 🤖 IA Conseiller — Powered by Claude AI")

    # Génération automatique des recommandations
    if "recommandations_ia" not in st.session_state:
        with st.spinner("🧠 Génération des recommandations IA en cours..."):
            st.session_state.recommandations_ia = generer_recommandations(
                df, consolidations, modal_shifts, synthese
            )

    col_reco, col_chat = st.columns([3, 2])

    with col_reco:
        st.markdown("### 📋 Recommandations automatiques")
        st.markdown(
            f'<div class="alert-box">{st.session_state.recommandations_ia}</div>',
            unsafe_allow_html=True
        )
        if st.button("🔄 Régénérer les recommandations"):
            del st.session_state["recommandations_ia"]
            st.rerun()

    with col_chat:
        st.markdown("### 💬 Questions suggérées")
        questions_suggerees = [
            "Quelles sont mes 3 priorités vertes ?",
            "Quel mode de transport dois-je éliminer en premier ?",
            "Comment réduire de 30% en 6 mois ?",
            "Quel est mon score vs la concurrence ?",
            "Quels sont mes risques CSRD ?",
        ]
        for q in questions_suggerees:
            if st.button(q, key=f"q_{q[:20]}"):
                st.session_state["question_selectionnee"] = q

        st.markdown("---")
        st.markdown("### 🗨️ Poser une question")
        question_libre = st.text_area(
            "Votre question",
            value=st.session_state.get("question_selectionnee", ""),
            placeholder="Ex : Quelles routes dois-je électrifier en priorité ?",
            height=80,
            label_visibility="collapsed"
        )

        if st.button("🚀 Demander à Claude", use_container_width=True):
            if question_libre.strip():
                with st.spinner("🤔 Claude analyse votre réseau..."):
                    reponse = repondre_question(question_libre, res)
                st.markdown("**Réponse :**")
                st.markdown(
                    f'<div class="alert-box">{reponse}</div>',
                    unsafe_allow_html=True
                )
                if "question_selectionnee" in st.session_state:
                    del st.session_state["question_selectionnee"]
            else:
                st.warning("⚠️ Entrez une question avant de cliquer.")

    st.markdown("---")
    st.markdown("### 📊 Synthèse pour le jury")
    c1, c2, c3 = st.columns(3)
    c1.metric("Routes analysées", res["nb_routes"])
    c2.metric("Intensité carbone", f"{res['intensite_moyenne']:.1f} gCO₂/t-km")
    c3.metric("vs Benchmark industrie",
              f"{res['benchmark_delta']:+.1f}%",
              delta_color="inverse" if res["benchmark_delta"] > 0 else "normal")


# ════════════════════════════════════════════════════════════════
# ONGLET 4 — RAPPORT ESG
# ════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("## 📄 Rapport ESG — Conformité CSRD 2024")

    col_info, col_gen = st.columns([2, 1])

    with col_info:
        st.markdown("### 📋 Aperçu du rapport")
        st.markdown(f"""
| Élément | Valeur |
|---|---|
| **Entreprise** | {nom_entreprise} |
| **Période** | {periode_rapport} |
| **Norme** | GLEC Framework v3.0 |
| **Conformité** | CSRD 2024 / ESRS E1 |
| **CO₂ total** | {res['total_co2_kg']:,.1f} kg CO₂e |
| **Score** | {res['score_environnemental']:.0f} / 100 |
| **Réduction potentielle** | -{synthese['pct_reduction_total']:.0f}% |
| **Pages** | 6 pages |
""")

        st.markdown("**Le rapport inclut :**")
        st.markdown("""
- ✅ Page de couverture avec score environnemental
- ✅ 4 KPIs principaux (CO₂, coût, score, économies)
- ✅ Tableau détaillé routes avec code couleur ROUGE/ORANGE/VERT
- ✅ Plan d'optimisation chiffré (consolidations + modal shifts)
- ✅ Section narrative ESG rédigée par Claude (IA)
- ✅ Projection -30% CO₂ alignée Paris Agreement
- ✅ Feuille de route d'implémentation sur 12 mois
""")

    with col_gen:
        st.markdown("### ⚙️ Génération")
        st.info("🔄 La génération prend ~5 secondes (rédigée par Claude si API configurée)")

        if st.button("📄 Générer le rapport PDF complet", use_container_width=True):
            with st.spinner("📝 Rédaction du rapport en cours..."):
                try:
                    # Rédaction section ESG par Claude
                    texte_esg = rediger_section_esg(res, synthese)

                    # Génération PDF
                    pdf_bytes = generer_rapport_pdf(
                        df=df,
                        resume=res,
                        consolidations=consolidations,
                        modal_shifts=modal_shifts,
                        texte_esg=texte_esg,
                        synthese=synthese,
                        entreprise=nom_entreprise,
                        periode=periode_rapport,
                    )
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.success("✅ Rapport généré avec succès !")
                except Exception as e:
                    st.error(f"❌ Erreur génération PDF : {e}")

        # Bouton téléchargement
        if "pdf_bytes" in st.session_state:
            nom_fichier = f"rapport_esg_{nom_entreprise.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label="⬇️ Télécharger le rapport PDF",
                data=st.session_state["pdf_bytes"],
                file_name=nom_fichier,
                mime="application/pdf",
                use_container_width=True,
            )
            st.caption(f"📁 {len(st.session_state['pdf_bytes'])//1024} Ko")

    st.markdown("---")

    # Section narrative ESG en aperçu texte
    st.markdown("### 📝 Aperçu — Section narrative ESG")
    st.markdown(f"""
> **Émissions de Scope 3 — Transport et Logistique**
>
> Pour la période **{periode_rapport}**, les émissions totales de transport de 
> **{nom_entreprise}** s'élèvent à **{res['total_co2_tonnes']:.3f} tCO₂e**, calculées 
> selon le **GLEC Framework v3.0** (Smart Freight Centre, 2023).
>
> Intensité carbone : **{res['intensite_moyenne']:.1f} gCO₂e/tonne-km**
> Score environnemental : **{res['score_environnemental']:.0f}/100**
>
> Notre plan de réduction vise **-{synthese['pct_reduction_total']:.0f}% d'ici 12 mois**, 
> aligné sur l'Accord de Paris et les objectifs Net Zéro 2050 de l'UE.
> Ce rapport est conforme aux exigences **CSRD 2024** (ESRS E1 — Changement climatique).
""")

    st.caption(
        "🔬 Données : GLEC Framework v3.0 — Smart Freight Centre | "
        "💰 Prix carbone : EU ETS 65 €/tCO₂ | "
        "🤖 IA : Claude (Anthropic) | "
        "🎓 Green Logistics Optimizer — Projet étudiant"
    )
