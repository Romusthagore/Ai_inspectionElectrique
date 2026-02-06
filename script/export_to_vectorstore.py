#!/usr/bin/env python3
"""
Script d'export des données Excel vers le format VectorStore
"""

import pandas as pd
import json
import sys

def export_excel_to_vectorstore(excel_path: str, output_json: str = "vectorstore_documents.json"):
    """
    Exporte les données Excel vers le format VectorStore
    """
    try:
        # Charger le fichier Excel
        print(f"📥 Chargement du fichier: {excel_path}")
        df = pd.read_excel(excel_path)

        print(f"✅ Fichier chargé: {len(df)} lignes")
        print(f"Colonnes: {list(df.columns)}")

        # Créer des documents pour le VectorStore
        documents = []

        for idx, row in df.iterrows():
            verbe = str(row['Verbe']).strip() if pd.notna(row['Verbe']) else ""
            complement = str(row['Complément']).strip() if pd.notna(row['Complément']) else ""
            reference = str(row['ART_LIBELLE']).strip() if pd.notna(row['ART_LIBELLE']) else ""

            # Créer une phrase complète
            if verbe and complement:
                # Option 1: Phrase simple
                phrase = f"{verbe} {complement}"

                # Option 2: Phrase avec référence
                # phrase = f"{verbe} {complement} ({reference})" if reference else f"{verbe} {complement}"

                documents.append({
                    "id": len(documents),
                    "content": phrase,
                    "metadata": {
                        "verbe": verbe,
                        "complement": complement,
                        "reference": reference,
                        "original_row": idx + 2  # +2 car Excel commence à 1 et header à 1
                    }
                })

            # Progression
            if (idx + 1) % 100 == 0:
                print(f"  Traité {idx + 1}/{len(df)} lignes...")

        # Sauvegarder au format JSON
        print(f"\n💾 Sauvegarde dans: {output_json}")
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)

        # Statistiques
        print(f"\n📊 STATISTIQUES:")
        print(f"  Documents créés: {len(documents)}")
        print(f"  Lignes ignorées (Verbe ou Complément manquant): {len(df) - len(documents)}")

        if documents:
            # Afficher des exemples
            print(f"\n📝 EXEMPLES DE DOCUMENTS CRÉÉS:")
            for i, doc in enumerate(documents[:3]):
                print(f"  {i+1}. '{doc['content'][:80]}...'")

        return True

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Fonction principale"""
    print("=" * 60)
    print("📤 EXPORT DES DONNÉES EXCEL VERS VECTORSTORE")
    print("=" * 60)

    # Chemin vers votre fichier Excel
    EXCEL_PATH = "/home/student24/Downloads/Mes projets/PROJET RAPPORTS/Rapport/LEL24 V1 (02-2013).xls"

    # Chemin de sortie
    OUTPUT_JSON = "vectorstore_documents.json"

    print(f"\nFichier source: {EXCEL_PATH}")
    print(f"Fichier destination: {OUTPUT_JSON}")

    confirmation = input("\nConfirmer l'export (o/n)? ").strip().lower()

    if confirmation != 'o':
        print("❌ Export annulé")
        return

    # Exécuter l'export
    success = export_excel_to_vectorstore(EXCEL_PATH, OUTPUT_JSON)

    if success:
        print("\n" + "=" * 60)
        print("✅ EXPORT RÉUSSI!")
        print("=" * 60)
        print("\n🎯 PROCHAINES ÉTAPES:")
        print("1. Utilisez le fichier 'vectorstore_documents.json' pour reconstruire votre VectorStore")
        print("2. Testez avec quelques verbes")
        print("3. Mesurez l'amélioration du Recall@5")
    else:
        print("\n❌ L'export a échoué. Vérifiez le chemin du fichier.")

if __name__ == "__main__":
    main()
