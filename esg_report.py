"""
esg_report.py — Génération du rapport ESG PDF avec ReportLab
=============================================================
Produit un rapport professionnel de 7 pages conforme CSRD 2024.
"""

import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Palette de couleurs verte (identité visuelle du projet)
VERT_FONCE  = colors.HexColor("#1B4332")
VERT_MOYEN  = colors.HexColor("#2D6A4F")
VERT_CLAIR  = colors.HexColor("#52B788")
VERT_PALE   = colors.HexColor("#D8F3DC")
ROUGE       = colors.HexColor("#C0392B")
ORANGE      = colors.HexColor("#E67E22")
GRIS_TEXTE  = colors.HexColor("#2C3E50")
GRIS_FOND   = colors.HexColor("#F8F9FA")
BLANC       = colors.white


def _styles():
    """Crée et retourne le dictionnaire de styles ReportLab."""
    s = getSampleStyleSheet()
    custom = {
        "titre_couv": ParagraphStyle("titre_couv", fontName="Helvetica-Bold",
            fontSize=28, textColor=BLANC, alignment=TA_CENTER, spaceAfter=12),
        "sous_titre_couv": ParagraphStyle("sous_titre_couv", fontName="Helvetica",
            fontSize=14, textColor=VERT_PALE, alignment=TA_CENTER, spaceAfter=8),
        "score_couv": ParagraphStyle("score_couv", fontName="Helvetica-Bold",
            fontSize=72, textColor=VERT_CLAIR, alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold",
            fontSize=18, textColor=VERT_FONCE, spaceBefore=16, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold",
            fontSize=13, textColor=VERT_MOYEN, spaceBefore=10, spaceAfter=6),
        "body": ParagraphStyle("body", fontName="Helvetica",
            fontSize=10, textColor=GRIS_TEXTE, leading=15, spaceAfter=6),
        "kpi_val": ParagraphStyle("kpi_val", fontName="Helvetica-Bold",
            fontSize=22, textColor=VERT_FONCE, alignment=TA_CENTER),
        "kpi_lbl": ParagraphStyle("kpi_lbl", fontName="Helvetica",
            fontSize=9, textColor=GRIS_TEXTE, alignment=TA_CENTER),
        "footer": ParagraphStyle("footer", fontName="Helvetica",
            fontSize=8, textColor=colors.grey, alignment=TA_CENTER),
        "encadre": ParagraphStyle("encadre", fontName="Helvetica-Oblique",
            fontSize=10, textColor=VERT_FONCE, leading=14,
            leftIndent=12, rightIndent=12),
    }
    return {**{k: s[k] for k in s.byName}, **custom}


def _couleur_risque(niveau: str):
    """Retourne la couleur ReportLab selon le niveau de risque."""
    return {"ROUGE": ROUGE, "ORANGE": ORANGE, "VERT": VERT_CLAIR}.get(niveau, GRIS_TEXTE)


def _page_couverture(elements, styles, resume, entreprise, periode):
    """Génère la page de couverture du rapport."""
    score = resume.get("score_environnemental", 50)
    co2   = resume.get("total_co2_kg", 0)

    # Fond coloré simulé avec un tableau pleine largeur
    data_couv = [[Paragraph(
        f"<b>🌿 GREEN LOGISTICS OPTIMIZER</b>", styles["titre_couv"])]]
    t = Table(data_couv, colWidths=[17*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), VERT_FONCE),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING", (0,0), (-1,-1), 30),
        ("BOTTOMPADDING", (0,0), (-1,-1), 30),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph(
        "Rapport ESG — Émissions Scope 3 Logistiques", styles["sous_titre_couv"]))
    elements.append(Paragraph(f"<b>{entreprise}</b>", styles["h1"]))
    elements.append(Paragraph(f"Période : {periode}", styles["body"]))
    elements.append(Paragraph(
        f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles["body"]))
    elements.append(HRFlowable(width="100%", color=VERT_CLAIR, thickness=2))
    elements.append(Spacer(1, 1*cm))

    # Score géant
    elements.append(Paragraph("Score Environnemental", styles["h2"]))
    elements.append(Paragraph(f"{score:.0f}", styles["score_couv"]))
    elements.append(Paragraph("/ 100  (méthode GLEC Framework 2023)", styles["kpi_lbl"]))
    elements.append(Spacer(1, 0.8*cm))

    # Badge couleur selon score
    if score >= 70:
        badge_color, badge_txt = VERT_CLAIR, "🟢 BON NIVEAU"
    elif score >= 45:
        badge_color, badge_txt = ORANGE, "🟠 À AMÉLIORER"
    else:
        badge_color, badge_txt = ROUGE, "🔴 ACTION URGENTE"

    data_badge = [[Paragraph(f"<b>{badge_txt}</b>", styles["kpi_val"])]]
    tb = Table(data_badge, colWidths=[8*cm])
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), badge_color),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elements.append(tb)
    elements.append(Spacer(1, 1*cm))

    elements.append(Paragraph(
        f"CO₂ total réseau : <b>{co2:,.1f} kg CO₂e</b> | "
        f"Conformité : <b>CSRD 2024 / GLEC v3.0</b>", styles["body"]))
    elements.append(PageBreak())


def _page_resume_executif(elements, styles, resume, synthese):
    """Page 2 — Résumé exécutif avec 4 KPIs."""
    elements.append(Paragraph("1. Résumé Exécutif", styles["h1"]))
    elements.append(HRFlowable(width="100%", color=VERT_CLAIR, thickness=1.5))
    elements.append(Spacer(1, 0.4*cm))

    # 4 KPIs en tableau
    co2_kg   = resume.get("total_co2_kg", 0)
    cout_eur = resume.get("total_cout_eur", 0)
    score    = resume.get("score_environnemental", 0)
    eco_co2  = synthese.get("co2_total_eco", 0) if synthese else 0

    kpi_data = [[
        Paragraph(f"{co2_kg:,.1f}", styles["kpi_val"]),
        Paragraph(f"{cout_eur:,.2f}", styles["kpi_val"]),
        Paragraph(f"{score:.0f}/100", styles["kpi_val"]),
        Paragraph(f"{eco_co2:,.0f}", styles["kpi_val"]),
    ],[
        Paragraph("kg CO₂e total", styles["kpi_lbl"]),
        Paragraph("€ coût carbone EU ETS", styles["kpi_lbl"]),
        Paragraph("Score environnemental", styles["kpi_lbl"]),
        Paragraph("kg CO₂ économisables", styles["kpi_lbl"]),
    ]]

    t_kpi = Table(kpi_data, colWidths=[4.2*cm]*4)
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), VERT_PALE),
        ("GRID", (0,0), (-1,-1), 0.5, VERT_CLAIR),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 0.6*cm))

    # Répartition CO₂ par mode (tableau texte car pas de graphe sans matplotlib)
    repartition = resume.get("repartition_co2_mode", {})
    if repartition:
        elements.append(Paragraph("Répartition CO₂ par mode de transport", styles["h2"]))
        rows = [["Mode", "CO₂ (kg)", "Part (%)"]]
        for label, data in sorted(repartition.items(), key=lambda x: x[1]["co2_kg"], reverse=True):
            rows.append([
                Paragraph(f"{data.get('emoji','')} {label}", styles["body"]),
                Paragraph(f"{data['co2_kg']:,.1f}", styles["body"]),
                Paragraph(f"{data['pct']:.1f}%", styles["body"]),
            ])
        t_rep = Table(rows, colWidths=[9*cm, 4*cm, 4*cm])
        t_rep.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), VERT_FONCE),
            ("TEXTCOLOR", (0,0), (-1,0), BLANC),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [BLANC, VERT_PALE]),
            ("ALIGN", (1,0), (-1,-1), "CENTER"),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        elements.append(t_rep)

    elements.append(PageBreak())


def _page_analyse_routes(elements, styles, df):
    """Page 3 — Tableau détaillé de toutes les routes."""
    elements.append(Paragraph("2. Analyse Détaillée par Route", styles["h1"]))
    elements.append(HRFlowable(width="100%", color=VERT_CLAIR, thickness=1.5))
    elements.append(Spacer(1, 0.4*cm))

    header = ["Origine", "Destination", "Mode", "Dist. (km)", "Poids (t)", "CO₂ (kg)", "Niveau"]
    rows = [header]

    for _, row in df.iterrows():
        niveau = row.get("niveau_risque", "ORANGE")
        rows.append([
            str(row["origine"]),
            str(row["destination"]),
            str(row.get("label_mode", row["mode"]))[:20],
            f"{row['distance_km']:.0f}",
            f"{row['poids_tonnes']:.1f}",
            f"{row.get('co2_kg', 0):,.1f}",
            niveau,
        ])

    col_w = [3.5*cm, 3.5*cm, 4*cm, 2*cm, 2*cm, 2*cm, 1.5*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)

    style_cmds = [
        ("BACKGROUND", (0,0), (-1,0), VERT_FONCE),
        ("TEXTCOLOR", (0,0), (-1,0), BLANC),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.4, colors.lightgrey),
        ("ALIGN", (3,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]

    # Couleur de la colonne "Niveau"
    for i, row_data in enumerate(rows[1:], 1):
        niveau = row_data[-1]
        c = {"ROUGE": ROUGE, "ORANGE": ORANGE, "VERT": VERT_CLAIR}.get(niveau, colors.grey)
        style_cmds.append(("BACKGROUND", (-1, i), (-1, i), c))
        style_cmds.append(("TEXTCOLOR", (-1, i), (-1, i), BLANC))
        style_cmds.append(("FONTNAME", (-1, i), (-1, i), "Helvetica-Bold"))

    t.setStyle(TableStyle(style_cmds))
    elements.append(t)
    elements.append(PageBreak())


def _page_optimisations(elements, styles, consolidations, modal_shifts):
    """Page 4 — Plan d'optimisation chiffré."""
    elements.append(Paragraph("3. Plan d'Optimisation", styles["h1"]))
    elements.append(HRFlowable(width="100%", color=VERT_CLAIR, thickness=1.5))
    elements.append(Spacer(1, 0.4*cm))

    # Consolidations
    elements.append(Paragraph("3.1 Consolidation de chargements", styles["h2"]))
    if consolidations:
        rows_c = [["ID", "Trajet", "CO₂ économisé", "Réduction", "Économie €", "Faisabilité"]]
        for c in consolidations:
            rows_c.append([
                c["id"],
                f"{c['origines']} → {c['destinations']}",
                f"{c['co2_economise']:.1f} kg",
                f"-{c['pct_reduction']:.0f}%",
                f"{c['economie_eur']:.2f} €",
                c["faisabilite"],
            ])
        t_c = Table(rows_c, colWidths=[1.8*cm, 5*cm, 2.5*cm, 2*cm, 2.2*cm, 2.5*cm])
        t_c.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), VERT_MOYEN),
            ("TEXTCOLOR", (0,0), (-1,0), BLANC),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.4, colors.lightgrey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [BLANC, VERT_PALE]),
            ("ALIGN", (2,0), (-1,-1), "CENTER"),
        ]))
        elements.append(t_c)
    else:
        elements.append(Paragraph("Aucune opportunité de consolidation détectée.", styles["body"]))

    elements.append(Spacer(1, 0.5*cm))

    # Modal shifts
    elements.append(Paragraph("3.2 Report modal (camion → train / électrique)", styles["h2"]))
    if modal_shifts:
        rows_m = [["ID", "Trajet", "Mode cible", "CO₂ économisé", "Réduction"]]
        for ms in modal_shifts:
            opt = ms["meilleure_option"]
            rows_m.append([
                ms["id"],
                f"{ms['origine']} → {ms['destination']}",
                opt["mode_cible"],
                f"{opt['co2_economise']:.1f} kg",
                f"-{opt['pct_reduction']:.0f}%",
            ])
        t_m = Table(rows_m, colWidths=[1.8*cm, 5.5*cm, 4*cm, 2.5*cm, 2.2*cm])
        t_m.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), VERT_MOYEN),
            ("TEXTCOLOR", (0,0), (-1,0), BLANC),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.4, colors.lightgrey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [BLANC, VERT_PALE]),
            ("ALIGN", (3,0), (-1,-1), "CENTER"),
        ]))
        elements.append(t_m)
    else:
        elements.append(Paragraph("Aucun report modal recommandé.", styles["body"]))

    elements.append(PageBreak())


def _page_esg_narrative(elements, styles, texte_esg, resume, synthese):
    """Page 5 — Section narrative ESG rédigée par Claude."""
    elements.append(Paragraph("4. Section Narrative ESG — Conformité CSRD", styles["h1"]))
    elements.append(HRFlowable(width="100%", color=VERT_CLAIR, thickness=1.5))
    elements.append(Spacer(1, 0.4*cm))

    note_csrd = (
        "📋 Ce texte est conforme aux exigences de la directive CSRD 2024 "
        "(Corporate Sustainability Reporting Directive) et du standard ESRS E1 "
        "(Changement climatique). Il peut être copié directement dans votre rapport annuel."
    )
    elements.append(Paragraph(note_csrd, styles["encadre"]))
    elements.append(Spacer(1, 0.4*cm))

    for para in texte_esg.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("##"):
            elements.append(Paragraph(para.replace("##", "").strip(), styles["h2"]))
        elif para.startswith("#"):
            elements.append(Paragraph(para.replace("#", "").strip(), styles["h1"]))
        else:
            elements.append(Paragraph(para, styles["body"]))
        elements.append(Spacer(1, 0.2*cm))

    elements.append(PageBreak())


def _page_projection(elements, styles, resume, synthese):
    """Page 6 — Projection et objectifs Paris Agreement."""
    elements.append(Paragraph("5. Projection — Objectif -30% CO₂ sur 12 mois", styles["h1"]))
    elements.append(HRFlowable(width="100%", color=VERT_CLAIR, thickness=1.5))
    elements.append(Spacer(1, 0.4*cm))

    co2_act = resume.get("total_co2_kg", 0)
    eco_tot = synthese.get("co2_total_eco", 0) if synthese else 0
    co2_opt = max(0, co2_act - eco_tot)
    pct_red = synthese.get("pct_reduction_total", 0) if synthese else 0
    objectif_paris = co2_act * 0.70  # -30% = objectif Paris

    data_proj = [
        ["Scénario", "CO₂ (kg)", "Variation", "Statut"],
        ["Réseau actuel", f"{co2_act:,.1f}", "Référence", "📊 Baseline"],
        ["Après optimisations", f"{co2_opt:,.1f}", f"-{pct_red:.0f}%", "🎯 Atteignable"],
        ["Objectif Paris Agreement", f"{objectif_paris:,.1f}", "-30%", "✅ Aligné ODD 13"],
    ]
    t = Table(data_proj, colWidths=[5.5*cm, 3.5*cm, 3*cm, 5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), VERT_FONCE),
        ("TEXTCOLOR", (0,0), (-1,0), BLANC),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND", (0,2), (-1,2), VERT_PALE),
        ("BACKGROUND", (0,3), (-1,3), colors.HexColor("#E8F5E9")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.8*cm))

    timeline = [
        ["Phase", "Période", "Action", "Réduction visée"],
        ["1 — Quick wins", "Mois 1-3", "Consolidations chargements", f"-{synthese.get('co2_consolid_eco',0):,.0f} kg CO₂" if synthese else "—"],
        ["2 — Modal shift", "Mois 4-6", "Report vers train électrique", f"-{synthese.get('co2_modal_eco',0):,.0f} kg CO₂" if synthese else "—"],
        ["3 — Électrification", "Mois 7-12", "Pilote camions électriques", f"-{synthese.get('co2_ev_eco',0):,.0f} kg CO₂" if synthese else "—"],
    ]
    t2 = Table(timeline, colWidths=[3.5*cm, 2.5*cm, 6*cm, 4*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), VERT_MOYEN),
        ("TEXTCOLOR", (0,0), (-1,0), BLANC),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [BLANC, VERT_PALE]),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    elements.append(Paragraph("Feuille de route d'implémentation", styles["h2"]))
    elements.append(t2)

    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        "Source des facteurs d'émission : GLEC Framework v3.0 — Smart Freight Centre (2023) | "
        "Prix carbone : EU ETS 2024 (65 €/tCO₂) | "
        "Green Logistics Optimizer — Outil open-source étudiant",
        styles["footer"]
    ))


def generer_rapport_pdf(
    df,
    resume: dict,
    consolidations: list,
    modal_shifts: list,
    texte_esg: str,
    synthese: dict = None,
    entreprise: str = "Mon Entreprise",
    periode: str = "Janvier 2024",
) -> bytes:
    """
    Génère le rapport ESG complet en PDF et retourne les bytes.

    Args:
        df             : DataFrame enrichi (analyser_reseau)
        resume         : Résumé réseau (resume_reseau)
        consolidations : Liste consolidations (detecter_consolidations)
        modal_shifts   : Liste modal shifts (detecter_modal_shifts)
        texte_esg      : Texte narratif ESG (advisor.rediger_section_esg)
        synthese       : Synthèse globale optimisations
        entreprise     : Nom de l'entreprise (affiché en couverture)
        periode        : Période de reporting (ex: "Janvier 2024")

    Returns:
        Contenu PDF en bytes (prêt pour st.download_button)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
        title=f"Rapport ESG — {entreprise}",
        author="Green Logistics Optimizer",
        subject="Émissions Scope 3 Logistiques — CSRD 2024",
    )

    styles = _styles()
    elements = []

    # Construction des pages
    _page_couverture(elements, styles, resume, entreprise, periode)
    _page_resume_executif(elements, styles, resume, synthese)
    _page_analyse_routes(elements, styles, df)
    _page_optimisations(elements, styles, consolidations, modal_shifts)
    _page_esg_narrative(elements, styles, texte_esg, resume, synthese)
    _page_projection(elements, styles, resume, synthese)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ── Test rapide
if __name__ == "__main__":
    import os
    from calculator import analyser_reseau, resume_reseau
    from optimizer import optimiser_reseau
    from advisor import rediger_section_esg

    chemin = os.path.join(os.path.dirname(__file__), "data", "sample_routes.csv")
    df  = analyser_reseau(chemin)
    res = resume_reseau(df)
    opt = optimiser_reseau(df)
    esg = rediger_section_esg(res, opt["synthese"])
    pdf = generer_rapport_pdf(
        df, res,
        opt["consolidations"], opt["modal_shifts"],
        esg, opt["synthese"],
        entreprise="Demo Corp", periode="Janvier 2024"
    )
    out = "rapport_esg_demo.pdf"
    with open(out, "wb") as f:
        f.write(pdf)
    print(f"✅ Rapport généré : {out} ({len(pdf)//1024} Ko)")
