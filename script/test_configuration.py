#!/usr/bin/env python3
"""
Script de test complet pour groq_config.py et config.py
"""
import sys
import os

# Ajoute le chemin du projet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_groq_config():
    """Teste le fichier groq_config.py"""
    print("🧪 TEST DE groq_config.py")
    print("=" * 50)
    
    try:
        # Test d'import
        from groq_config import (
            GROQ_CONFIG, 
            AVAILABLE_MODELS, 
            GroqLLMClient,
            list_available_models,
            test_connection,
            get_model_info
        )
        print("✅ Import de groq_config.py réussi")
        
        # Test des constantes
        print(f"✅ GROQ_CONFIG chargé: {list(GROQ_CONFIG.keys())}")
        print(f"✅ Modèles disponibles: {len(AVAILABLE_MODELS)} catégories")
        
        # Test de la fonction list_available_models
        print("\n📋 Liste des modèles:")
        list_available_models()
        
        # Test des informations modèle
        model_info = get_model_info("llama-3.3-70b-versatile")
        print(f"✅ Info modèle: {model_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur groq_config.py: {e}")
        return False

def test_config():
    """Teste le fichier config.py"""
    print("\n\n🧪 TEST DE config.py")
    print("=" * 50)
    
    try:
        # Test d'import
        from config import (
            BASE_DIR, DATA_DIR, FAISS_INDEX_PATH, METADATA_PATH,
            get_llm_client, get_available_models, test_llm_connection,
            valider_configuration, initialiser_repertoires,
            SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE
        )
        print("✅ Import de config.py réussi")
        
        # Test des chemins
        print(f"✅ BASE_DIR: {BASE_DIR} (existe: {BASE_DIR.exists()})")
        print(f"✅ DATA_DIR: {DATA_DIR} (existe: {DATA_DIR.exists()})")
        print(f"✅ FAISS_INDEX_PATH: {FAISS_INDEX_PATH} (existe: {FAISS_INDEX_PATH.exists()})")
        print(f"✅ METADATA_PATH: {METADATA_PATH} (existe: {METADATA_PATH.exists()})")
        
        # Test des prompts
        print(f"✅ SYSTEM_PROMPT: {len(SYSTEM_PROMPT)} caractères")
        print(f"✅ RAG_PROMPT_TEMPLATE: {len(RAG_PROMPT_TEMPLATE)} caractères")
        
        # Test de la validation
        print("\n🔍 Validation configuration...")
        valider_configuration()
        
        # Test de l'initialisation des répertoires
        print("\n📁 Initialisation répertoires...")
        initialiser_repertoires()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur config.py: {e}")
        return False

def test_llm_integration():
    """Test l'intégration entre groq_config et config"""
    print("\n\n🔗 TEST D'INTÉGRATION LLM")
    print("=" * 50)
    
    try:
        from config import get_llm_client, get_available_models, test_llm_connection
        
        # Test de la connexion LLM
        print("🔌 Test de connexion LLM...")
        connection_ok = test_llm_connection()
        
        if connection_ok:
            # Test du client LLM
            print("\n🤖 Test du client LLM...")
            llm = get_llm_client()
            
            # Test simple
            test_prompt = "Réponds uniquement par 'TEST RÉUSSI'"
            response = llm.invoke(test_prompt)
            print(f"✅ Réponse LLM: {response.strip()}")
            
            # Test des modèles disponibles
            print("\n📊 Modèles disponibles via config:")
            available_models = get_available_models()
            for category, models in available_models.items():
                print(f"  {category}: {len(models)} modèles")
                
        return connection_ok
        
    except Exception as e:
        print(f"❌ Erreur intégration LLM: {e}")
        return False

def test_multi_model():
    """Test la fonction multi-modèles"""
    print("\n\n🔄 TEST MULTI-MODÈLES")
    print("=" * 50)
    
    try:
        from config import test_different_models
        
        # Test avec une question simple
        test_question = "Quelles sont les principales normes électriques en France?"
        
        print("🧪 Lancement du test multi-modèles...")
        test_different_models(test_question)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test multi-modèles: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 LANCEMENT DES TESTS DE CONFIGURATION")
    print("=" * 60)
    
    # Vérification de la clé API
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "gsk_your_api_key_here":
        print("⚠️  ATTENTION: Clé API Groq non configurée!")
        print("💡 Pour configurer:")
        print("   export GROQ_API_KEY='votre_clé_réelle'")
        print("   ou éditez votre fichier .env")
        print("\n📝 Tests continuent mais échoueront sur les parties LLM...")
    else:
        print(f"✅ Clé API trouvée: {api_key[:10]}...{api_key[-10:]}")
    
    # Exécution des tests
    tests = [
        ("groq_config.py", test_groq_config),
        ("config.py", test_config),
        ("Intégration LLM", test_llm_integration),
        ("Multi-modèles", test_multi_model),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} a échoué: {e}")
            results.append((test_name, False))
    
    # Rapport final
    print("\n\n📊 RAPPORT FINAL DES TESTS")
    print("=" * 60)
    
    for test_name, success in results:
        statsus = "✅ RÉUSSI" if success else "❌ ÉCHEC"
        print(f"{test_name}: {status}")
    
    total_success = sum(1 for _, success in results if success)
    print(f"\n🎯 Total: {total_success}/{len(results)} tests réussis")
    
    if total_success == len(results):
        print("\n🎉 TOUS LES TESTS SONT RÉUSSIS! Votre configuration est opérationnelle! 🚀")
    else:
        print(f"\n⚠️  {len(results) - total_success} test(s) ont échoué. Vérifiez les messages ci-dessus.")

if __name__ == "__main__":
    main()