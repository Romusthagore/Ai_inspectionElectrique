
#!/usr/bin/env python3
"""
Script de test rapide pour votre système d'autocomplétion
"""

import sys

def test_your_system():
    """Teste votre vrai système d'autocomplétion"""

    # ⚠️ IMPORTEZ VOTRE VRAI SYSTÈME ICI
    try:
        from suggestion_engine import get_suggestion_engine
        from langchain_groq import ChatGroq
        from vector_store import VectorStore

        print("🔧 Initialisation de votre système...")

        # Initialiser le LLM
        llm = ChatGroq(
            temperature=0.1,
            model_name="mixtral-8x7b-32768",
            groq_api_key="VOTRE_CLÉ_API"  # ⚠️ Remplacez
        )

        # Initialiser le VectorStore
        vectorstore = VectorStore()

        # Créer le moteur
        engine = get_suggestion_engine(vectorstore=vectorstore, llm=llm)

        # Fonction de test
        def autocomplete(query: str):
            suggestions = engine.get_suggestions(query)
            # Normaliser les suggestions
            normalized = []
            for sugg in suggestions:
                if isinstance(sugg, dict):
                    text = sugg.get('texte', sugg.get('contenu', sugg.get('complement', '')))
                    if text:
                        normalized.append(text.strip())
                else:
                    normalized.append(str(sugg).strip())
            return normalized

        return autocomplete

    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("⚠️ Mode simulation activé")
        return None

def main():
    """Test interactif"""
    print("=" * 60)
    print("🧪 TEST INTERACTIF - AUTOCOMPLÉTION PROGRESSIVE")
    print("=" * 60)

    # Essayer de charger votre système
    autocomplete_func = test_your_system()

    if autocomplete_func is None:
        print("\n📝 Mode simulation - entrez des suggestions manuellement")
        print("   (Pour utiliser votre vrai système, installez les modules)")

        def simulation_autocomplete(query: str):
            print(f"\n🔍 Requête: '{query}'")
            print("💡 Suggestions (entrez une par ligne, vide pour terminer):")

            suggestions = []
            while True:
                sugg = input("  > ").strip()
                if not sugg:
                    break
                suggestions.append(sugg)

            return suggestions

        autocomplete_func = simulation_autocomplete

    # Tests pré-définis
    test_queries = [
        "remplacer",
        "remplacer le",
        "remplacer le disjoncteur",
        "vérifier",
        "vérifier la",
        "vérifier la terre",
        "installer",
        "installer une",
        "installer une protection"
    ]

    print("\n🎯 TESTS PRÉ-DÉFINIS:")
    for query in test_queries:
        print(f"\n📝 Requête: '{query}'")
        suggestions = autocomplete_func(query)[:5]

        if suggestions:
            print("   Suggestions (top 5):")
            for i, sugg in enumerate(suggestions, 1):
                print(f"     {i}. {sugg[:60]}...")
        else:
            print("   Aucune suggestion")

    # Mode interactif
    print("\n" + "=" * 60)
    print("⌨️  MODE INTERACTIF (tapez 'quit' pour quitter)")
    print("=" * 60)

    while True:
        query = input("\nEntrez votre requête: ").strip()

        if query.lower() in ['quit', 'exit', 'q']:
            break

        if not query:
            continue

        suggestions = autocomplete_func(query)

        print(f"\n🔍 Requête: '{query}'")
        print(f"📊 {len(suggestions)} suggestions trouvées:")

        for i, sugg in enumerate(suggestions[:10], 1):
            print(f"  {i}. {sugg}")

        if len(suggestions) > 10:
            print(f"  ... et {len(suggestions) - 10} autres")

if __name__ == "__main__":
    main()
