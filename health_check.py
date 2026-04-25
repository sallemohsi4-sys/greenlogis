"""
health_check.py - Verification systeme avant demo
==================================================
Lance ce script avant votre presentation pour s'assurer
que tout fonctionne correctement.
Usage : python health_check.py
"""

import sys
import os
import importlib

# Fix encodage Windows (PowerShell / cmd)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check(label, fn):
    try:
        fn()
        print(f"  ✅ {label}")
        return True
    except Exception as e:
        print(f"  ❌ {label} → {e}")
        return False

def main():
    print("=" * 55)
    print("🔍 GREEN LOGISTICS OPTIMIZER — Vérification système")
    print("=" * 55)
    resultats = []

    # 1. Python
    print(f"\n[1] Python {sys.version.split()[0]}", end=" ")
    ok = sys.version_info >= (3, 9)
    print("✅" if ok else "❌ (requis ≥ 3.9)")
    resultats.append(ok)

    # 2. Packages
    print("\n[2] Packages requis :")
    pkgs = [
        ("pandas",       "pandas"),
        ("numpy",        "numpy"),
        ("streamlit",    "streamlit"),
        ("plotly",       "plotly"),
        ("folium",       "folium"),
        ("reportlab",    "reportlab"),
        ("anthropic",    "anthropic"),
        ("dotenv",       "dotenv"),
        ("streamlit_folium", "streamlit_folium"),
    ]
    for nom, mod in pkgs:
        ok_pkg = check(nom, lambda m=mod: importlib.import_module(m))
        resultats.append(ok_pkg)

    # 3. Fichiers projet
    print("\n[3] Fichiers du projet :")
    base = os.path.dirname(os.path.abspath(__file__))
    fichiers = [
        "emission_factors.py",
        "calculator.py",
        "optimizer.py",
        "advisor.py",
        "esg_report.py",
        "data/sample_routes.csv",
        "dashboard/app.py",
    ]
    for f in fichiers:
        chemin = os.path.join(base, f)
        ok_f = check(f, lambda c=chemin: open(c).close())
        resultats.append(ok_f)

    # 4. Données démo
    print("\n[4] Données démo :")
    def _test_csv():
        import pandas as pd
        df = pd.read_csv(os.path.join(base, "data", "sample_routes.csv"))
        assert len(df) >= 10, "CSV trop court"
        cols = ["origine","destination","mode","distance_km","poids_tonnes","date"]
        assert all(c in df.columns for c in cols), f"Colonnes manquantes"
    resultats.append(check("sample_routes.csv (structure OK)", _test_csv))

    # 5. Modules métier
    print("\n[5] Modules métier :")
    def _test_calc():
        sys.path.insert(0, base)
        from emission_factors import co2_kg
        r = co2_kg(240, 8, "camion_diesel_grand")
        assert abs(r - 184.32) < 1.0, f"Résultat inattendu : {r}"
    resultats.append(check("emission_factors.co2_kg()", _test_calc))

    def _test_analyser():
        from calculator import analyser_reseau, resume_reseau
        df = analyser_reseau(os.path.join(base, "data", "sample_routes.csv"))
        res = resume_reseau(df)
        assert res["total_co2_kg"] > 0
    resultats.append(check("calculator.analyser_reseau()", _test_analyser))

    def _test_optim():
        from calculator import analyser_reseau
        from optimizer import optimiser_reseau
        df = analyser_reseau(os.path.join(base, "data", "sample_routes.csv"))
        r  = optimiser_reseau(df)
        assert "synthese" in r
        assert r["synthese"]["pct_reduction_total"] > 0
    resultats.append(check("optimizer.optimiser_reseau()", _test_optim))

    # 6. Clé API Claude
    print("\n[6] API Claude :")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(base, ".env"))
    api_key = os.environ.get("ANTHROPIC_API_KEY","")
    if api_key and api_key != "your_anthropic_api_key_here":
        print("  ✅ ANTHROPIC_API_KEY configurée — Mode IA activé")
        resultats.append(True)
    else:
        print("  ⚠️  ANTHROPIC_API_KEY non configurée → Mode hors-ligne (fallback OK)")
        resultats.append(True)  # Pas bloquant

    # Bilan final
    nb_ok  = sum(resultats)
    nb_tot = len(resultats)
    print("\n" + "=" * 55)
    if nb_ok == nb_tot:
        print(f"🎉 TOUT EST OK ({nb_ok}/{nb_tot}) — Prêt pour la démo !")
        print("   Lancez : streamlit run dashboard/app.py")
    else:
        nb_err = nb_tot - nb_ok
        print(f"⚠️  {nb_err} problème(s) détecté(s) sur {nb_tot} vérifications.")
        print("   Installez les dépendances : pip install -r requirements.txt")
    print("=" * 55)

if __name__ == "__main__":
    main()
