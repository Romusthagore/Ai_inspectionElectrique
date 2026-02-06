#!/usr/bin/env python3
"""
Système de récupération OPTIMISÉ avec recherche hybride et cache
Intègre : filtrage similarité, cache intelligent, pré-filtrage textuel
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from functools import lru_cache
from core.vector_store import get_vector_store
from core.config import TOP_K

logger = logging.getLogger(__name__)


class Retriever:
    """
    Retriever OPTIMISÉ avec recherche hybride et cache
    """
    
    def __init__(
        self, 
        k: int = None,
        min_similarity: float = 0.65,
        enable_cache: bool = True
    ):
        """
        Initialise le Retriever optimisé
        
        Args:
            k: Nombre de résultats par défaut
            min_similarity: Seuil de similarité minimum
            enable_cache: Activer le cache pour verbes fréquents
        """
        self.vector_store = get_vector_store()
        self.default_k = k or TOP_K
        self.min_similarity = min_similarity
        self.enable_cache = enable_cache
        
        # ✅ NOUVEAU : Cache pour requêtes fréquentes
        self._cache = {}
        self._cache_stats = {"hits": 0, "misses": 0}
        
        # ✅ NOUVEAU : Métadonnées enrichies
        self._document_metadata = None
        
        if self.enable_cache:
            self._init_cache()
        
        logger.info(
            f"✅ Retriever OPTIMISÉ initialisé "
            f"(k={self.default_k}, min_sim={min_similarity}, cache={enable_cache})"
        )
    
    # =========================================================================
    # ✅ RECHERCHE HYBRIDE (Texte + Vecteurs)
    # =========================================================================
    
    def get_relevant_documents(
        self, 
        query: str, 
        k: int = None,
        min_similarity: float = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère documents avec recherche hybride OPTIMISÉE
        
        Args:
            query: Requête de recherche
            k: Nombre de résultats
            min_similarity: Seuil personnalisé (optionnel)
            
        Returns:
            Documents filtrés et enrichis
        """
        if not query or not query.strip():
            logger.warning("⚠️ Requête vide")
            return []
        
        start_time = time.time()
        k = k or self.default_k
        min_sim = min_similarity or self.min_similarity
        
        try:
            # ✅ ÉTAPE 1 : Vérifier cache
            cache_key = self._get_cache_key(query, k)
            if self.enable_cache and cache_key in self._cache:
                self._cache_stats["hits"] += 1
                logger.debug(f"🎯 Cache HIT pour '{query}'")
                return self._cache[cache_key]
            
            self._cache_stats["misses"] += 1
            
            # ✅ ÉTAPE 2 : Parser la requête
            verbe, complement = self._parser_query(query)
            
            # ✅ ÉTAPE 3 : Recherche adaptative
            if verbe and complement:
                # Recherche hybride avec pré-filtrage
                results = self._recherche_hybride(verbe, complement, k=k*2)
            else:
                # Recherche vectorielle simple
                results = self._recherche_vectorielle(query, k=k*2)
            
            # ✅ ÉTAPE 4 : Filtrage par similarité
            filtered_results = self._filter_by_similarity(results, min_sim)
            
            # ✅ ÉTAPE 5 : Enrichissement métadonnées
            enriched_results = self._enrich_results(filtered_results)
            
            # ✅ ÉTAPE 6 : Ranking final
            ranked_results = self._rank_results(enriched_results, verbe, complement)
            
            # Limiter au k demandé
            final_results = ranked_results[:k]
            
            # Mise en cache
            if self.enable_cache:
                self._cache[cache_key] = final_results
            
            # Logging performance
            latency = (time.time() - start_time) * 1000
            logger.info(
                f"✅ '{query}': {len(final_results)}/{len(results)} docs "
                f"(latence: {latency:.0f}ms, cache: {self._cache_stats['hits']}/{self._cache_stats['hits'] + self._cache_stats['misses']})"
            )
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Erreur recherche: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _recherche_hybride(
        self, 
        verbe: str, 
        complement: str, 
        k: int
    ) -> List[Dict]:
        """
        Recherche hybride : pré-filtrage textuel + recherche vectorielle
        """
        logger.debug(f"🔍 Recherche hybride: '{verbe}' + '{complement}'")
        
        # Construction requête complète
        query = f"{verbe} {complement}".strip()
        
        # Recherche vectorielle large
        results = self.vector_store.search(query, k=k)
        
        # Pré-filtrage par préfixe si complément fourni
        if complement:
            filtered = []
            complement_lower = complement.lower().strip()
            
            for doc in results:
                content = doc.get('content', '').lower()
                
                # Match si le contenu commence par le complément
                if content.startswith(complement_lower):
                    doc['prefix_match'] = True
                    filtered.append(doc)
                else:
                    doc['prefix_match'] = False
            
            # Si filtrage trop strict, garder résultats vectoriels
            if len(filtered) >= 3:
                logger.debug(f"✅ Pré-filtrage: {len(filtered)}/{len(results)} docs")
                return filtered
        
        return results
    
    def _recherche_vectorielle(self, query: str, k: int) -> List[Dict]:
        """
        Recherche vectorielle simple
        """
        return self.vector_store.search(query, k=k)
    
    def _filter_by_similarity(
        self, 
        results: List[Dict], 
        min_similarity: float
    ) -> List[Dict]:
        """
        Filtre résultats par seuil de similarité
        """
        filtered = []
        
        for doc in results:
            similarity = doc.get('similarity_score', 0.0)
            
            if similarity >= min_similarity:
                filtered.append(doc)
        
        if len(filtered) < len(results):
            logger.debug(
                f"🔍 Filtrage similarité: {len(filtered)}/{len(results)} docs "
                f"(seuil={min_similarity:.2f})"
            )
        
        return filtered
    
    def _rank_results(
        self, 
        results: List[Dict],
        verbe: Optional[str],
        complement: Optional[str]
    ) -> List[Dict]:
        """
        Ranking intelligent : prefix_match + popularité + similarité
        """
        for doc in results:
            score = 0.0
            
            # +50% si match exact du préfixe
            if doc.get('prefix_match', False):
                score += 0.5
            
            # +30% selon popularité (si disponible)
            popularite = doc.get('popularite', 0.5)
            score += popularite * 0.3
            
            # +20% selon similarité vectorielle
            similarity = doc.get('similarity_score', 0.5)
            score += similarity * 0.2
            
            doc['ranking_score'] = score
        
        # Tri par score décroissant
        results.sort(key=lambda x: x.get('ranking_score', 0), reverse=True)
        
        return results
    
    def _enrich_results(self, results: List[Dict]) -> List[Dict]:
        """
        Enrichit résultats avec métadonnées formatées
        """
        enriched = []
        
        for result in results:
            enriched_doc = {
                'content': result.get('content', ''),
                'source': result.get('source', ''),
                'type_document': result.get('type_document', ''),
                'norme': result.get('norme', ''),
                'article': result.get('article', ''),
                'similarity_score': result.get('similarity_score', 0.0),
                'ranking_score': result.get('ranking_score', 0.0),
                'prefix_match': result.get('prefix_match', False),
                'popularite': result.get('popularite', 0.5),
                'metadata': result.get('metadata', {})
            }
            enriched.append(enriched_doc)
        
        return enriched
    
    # =========================================================================
    # ✅ CACHE INTELLIGENT
    # =========================================================================
    
    def _init_cache(self):
        """
        Pré-charge le cache avec requêtes fréquentes
        """
        logger.info("🔄 Initialisation du cache...")
        
        # Requêtes fréquentes à pré-charger
        frequent_queries = [
            "protection différentielle",
            "mise à la terre",
            "disjoncteur",
            "câble",
            "tableau électrique",
            "parafoudre",
            "liaison équipotentielle",
            "schéma TT",
            "schéma TN",
            "schéma IT"
        ]
        
        for query in frequent_queries:
            try:
                cache_key = self._get_cache_key(query, self.default_k)
                results = self._recherche_vectorielle(query, k=self.default_k*2)
                filtered = self._filter_by_similarity(results, self.min_similarity)
                enriched = self._enrich_results(filtered)
                self._cache[cache_key] = enriched[:self.default_k]
            except Exception as e:
                logger.warning(f"⚠️ Erreur cache pour '{query}': {e}")
        
        logger.info(f"✅ Cache initialisé : {len(self._cache)} requêtes")
    
    def _get_cache_key(self, query: str, k: int) -> str:
        """
        Génère clé de cache normalisée
        """
        return f"{query.lower().strip()}:{k}"
    
    def clear_cache(self):
        """
        Vide le cache
        """
        self._cache.clear()
        self._cache_stats = {"hits": 0, "misses": 0}
        logger.info("🗑️ Cache vidé")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retourne statistiques du cache
        """
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "cache_size": len(self._cache),
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%"
        }
    
    # =========================================================================
    # MÉTHODES UTILITAIRES
    # =========================================================================
    
    def _parser_query(self, query: str) -> Tuple[str, str]:
        """
        Parse "remplacer le luminaire" → ("remplacer", "le luminaire")
        """
        mots = query.strip().split(maxsplit=1)
        
        if len(mots) == 1:
            return mots[0], ""
        else:
            return mots[0], mots[1]
    
    def search_by_category(
        self, 
        query: str, 
        doc_type: str = None, 
        k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche avec filtre par type de document
        """
        results = self.get_relevant_documents(query, k=k)
        
        if doc_type:
            filtered = [r for r in results if r.get('type_document') == doc_type]
            logger.info(f"🔍 Filtre '{doc_type}': {len(filtered)}/{len(results)} résultats")
            return filtered
        
        return results
    
    def get_document_types(self) -> List[str]:
        """
        Retourne types de documents disponibles
        """
        try:
            sample_results = self.vector_store.search("test", k=100)
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
        """
        try:
            test_results = self.get_relevant_documents("test", k=1)
            cache_stats = self.get_cache_stats()
            
            return {
                "status": "healthy",
                "vector_store_loaded": self.vector_store.is_loaded,
                "test_query_results": len(test_results),
                "default_k": self.default_k,
                "min_similarity": self.min_similarity,
                "cache_enabled": self.enable_cache,
                "cache_stats": cache_stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retourne statistiques détaillées
        """
        cache_stats = self.get_cache_stats()
        
        return {
            "retriever_config": {
                "default_k": self.default_k,
                "min_similarity": self.min_similarity,
                "cache_enabled": self.enable_cache
            },
            "cache": cache_stats,
            "vector_store": {
                "loaded": self.vector_store.is_loaded,
                "index_size": getattr(self.vector_store, 'index_size', 'N/A')
            }
        }


# =============================================================================
# SINGLETON ET FONCTIONS UTILITAIRES
# =============================================================================

_retriever_instance = None

def get_retriever(
    k: int = None,
    min_similarity: float = 0.65,
    enable_cache: bool = True
) -> Retriever:
    """
    Retourne l'instance singleton du Retriever
    """
    global _retriever_instance
    
    if _retriever_instance is None:
        _retriever_instance = Retriever(
            k=k,
            min_similarity=min_similarity,
            enable_cache=enable_cache
        )
    
    return _retriever_instance

def retrieve_documents(
    query: str, 
    k: int = None,
    min_similarity: float = None
) -> List[Dict[str, Any]]:
    """
    Fonction utilitaire pour recherche rapide
    """
    retriever = get_retriever()
    return retriever.get_relevant_documents(query, k=k, min_similarity=min_similarity)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST RETRIEVER OPTIMISÉ")
    print("=" * 60)
    
    try:
        # Initialisation
        retriever = get_retriever(min_similarity=0.65)
        print("✅ Retriever initialisé")
        
        # Test santé
        health = retriever.health_check()
        print(f"\n📊 Santé: {health['status']}")
        print(f"   Cache activé: {health['cache_enabled']}")
        print(f"   Cache stats: {health['cache_stats']}")
        
        # Test recherche
        print("\n" + "=" * 60)
        print("🔍 TESTS DE RECHERCHE")
        print("=" * 60)
        
        test_queries = [
            "protection différentielle",
            "remplacer le disjoncteur",
            "mise à la terre",
            "installer un transformateur"
        ]
        
        for query in test_queries:
            print(f"\n📝 Requête: '{query}'")
            results = retriever.get_relevant_documents(query, k=3)
            
            print(f"   {len(results)} résultats:")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.get('content', '')[:80]}...")
                print(f"      📊 Similarité: {result['similarity_score']:.3f} | "
                      f"Score: {result.get('ranking_score', 0):.3f} | "
                      f"Préfixe: {'✓' if result.get('prefix_match') else '✗'}")
                print(f"      📚 {result.get('norme', 'N/A')} - {result.get('article', 'N/A')}")
        
        # Test cache
        print("\n" + "=" * 60)
        print("💾 STATISTIQUES CACHE")
        print("=" * 60)
        stats = retriever.get_statistics()
        print(f"   Taille cache: {stats['cache']['cache_size']}")
        print(f"   Hit rate: {stats['cache']['hit_rate']}")
        print(f"   Hits: {stats['cache']['hits']}")
        print(f"   Misses: {stats['cache']['misses']}")
        
        # Test types de documents
        print("\n" + "=" * 60)
        print("📁 TYPES DE DOCUMENTS")
        print("=" * 60)
        doc_types = retriever.get_document_types()
        print(f"   Types disponibles: {', '.join(doc_types)}")
        
        print("\n" + "=" * 60)
        print("✅ RETRIEVER OPTIMISÉ PRÊT !")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test échoué: {e}")
        import traceback
        traceback.print_exc()