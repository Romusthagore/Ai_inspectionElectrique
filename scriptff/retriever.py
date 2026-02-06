#!/usr/bin/env python3
"""
Système de récupération de documents pour le pipeline RAG
Interface simple entre le VectorStore et le ContextBuilder
"""

import logging
from typing import List, Dict, Any, Optional
from vector_store import get_vector_store
from config import TOP_K

logger = logging.getLogger(__name__)


class Retriever:
    """
    Retriever pour la recherche de documents pertinents
    Version simple et robuste
    """
    
    def __init__(self, k: int = None):
        """
        Initialise le Retriever
        
        Args:
            k: Nombre de résultats par défaut (optionnel)
        """
        self.vector_store = get_vector_store()
        self.default_k = k or TOP_K
        
        logger.info(f"✅ Retriever initialisé (k={self.default_k})")
    
    def get_relevant_documents(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """
        Récupère les documents les plus pertinents pour une requête
        
        Args:
            query: Requête de recherche
            k: Nombre de résultats (défaut: self.default_k)
            
        Returns:
            Liste de documents avec métadonnées
        """
        if not query or not query.strip():
            logger.warning("⚠️ Requête vide")
            return []
        
        k = k or self.default_k
        
        try:
            logger.info(f"🔍 Recherche: '{query}' (k={k})")
            
            # Recherche dans le VectorStore
            results = self.vector_store.search(query, k=k)
            
            # Formater les résultats pour le ContextBuilder
            formatted_results = self._format_results(results)
            
            logger.info(f"✅ {len(formatted_results)} documents trouvés")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Erreur recherche: {e}")
            return []
    
    def _format_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """
        Formate les résultats pour le ContextBuilder
        
        Args:
            results: Résultats bruts du VectorStore
            
        Returns:
            Résultats formatés
        """
        formatted = []
        
        for result in results:
            formatted_doc = {
                'content': result.get('content', ''),
                'source': result.get('source', ''),
                'type_document': result.get('type_document', ''),
                'norme': result.get('norme', ''),
                'article': result.get('article', ''),
                'similarity_score': result.get('similarity_score', 0.0),
                'metadata': result.get('metadata', {})
            }
            formatted.append(formatted_doc)
        
        return formatted
    
    def search_by_category(self, query: str, doc_type: str = None, k: int = None) -> List[Dict[str, Any]]:
        """
        Recherche avec filtre par type de document
        
        Args:
            query: Requête de recherche
            doc_type: Type de document à filtrer
            k: Nombre de résultats
            
        Returns:
            Documents filtrés
        """
        results = self.get_relevant_documents(query, k=k)
        
        if doc_type:
            filtered = [r for r in results if r.get('type_document') == doc_type]
            logger.info(f"🔍 Filtre '{doc_type}': {len(filtered)}/{len(results)} résultats")
            return filtered
        
        return results
    
    def get_document_types(self) -> List[str]:
        """
        Retourne les types de documents disponibles
        
        Returns:
            Liste des types de documents
        """
        try:
            # Échantillonner pour obtenir les types
            sample_results = self.vector_store.search("test", k=50)
            doc_types = set()
            
            for result in sample_results:
                doc_type = result.get('type_document')
                if doc_type:
                    doc_types.add(doc_type)
            
            return sorted(list(doc_types))
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération types: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Vérifie l'état du Retriever
        
        Returns:
            Statut de santé
        """
        try:
            # Test basique
            test_results = self.get_relevant_documents("test", k=1)
            
            return {
                "status": "healthy",
                "vector_store_loaded": self.vector_store.is_loaded,
                "test_query_results": len(test_results),
                "default_k": self.default_k
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# =============================================================================
# SINGLETON ET FONCTIONS UTILITAIRES
# =============================================================================

_retriever_instance = None

def get_retriever(k: int = None) -> Retriever:
    """
    Retourne l'instance singleton du Retriever
    
    Args:
        k: Nombre de résultats par défaut
        
    Returns:
        Instance Retriever
    """
    global _retriever_instance
    
    if _retriever_instance is None:
        _retriever_instance = Retriever(k=k)
    
    return _retriever_instance

def retrieve_documents(query: str, k: int = None) -> List[Dict[str, Any]]:
    """
    Fonction utilitaire pour recherche rapide
    
    Args:
        query: Requête de recherche
        k: Nombre de résultats
        
    Returns:
        Documents pertinents
    """
    retriever = get_retriever()
    return retriever.get_relevant_documents(query, k=k)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print(" TEST RETRIEVER")
    print("=" * 50)
    
    try:
        # Initialisation
        retriever = get_retriever()
        print("Retriever initialisé")
        
        # Test santé
        health = retriever.health_check()
        print(f"  Santé: {health['status']}")
        
        # Test recherche
        test_queries = [
            "protection différentielle",
            "mise à la terre",
            "disjoncteur 30mA"
        ]
        
        for query in test_queries:
            print(f"\n🔍 '{query}':")
            results = retriever.get_relevant_documents(query, k=2)
            
            print(f"  {len(results)} résultats:")
            for i, result in enumerate(results, 1):
                print(f"     {i}. {result.get('norme', 'N/A')} - {result.get('article', 'N/A')}")
                print(f"        Score: {result['similarity_score']:.3f}")
                print(f"        Type: {result['type_document']}")
                print(f"        Source: {result['source']}")
        
        # Test types de documents
        doc_types = retriever.get_document_types()
        print(f"\n Types de documents disponibles: {', '.join(doc_types)}")
        
        print("\n RETRIEVER PRÊT POUR CONTEXT BUILDER!")
        
    except Exception as e:
        print(f" Test échoué: {e}")
        import traceback
        traceback.print_exc()