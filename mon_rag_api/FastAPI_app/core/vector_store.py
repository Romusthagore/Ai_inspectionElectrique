#!/usr/bin/env python3
"""
Module de gestion de la base vectorielle FAISS pour le pipeline RAG
Version CORRIGÉE - Compatible avec ta config actuelle
"""

import pickle
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np

# Import conditionnel pour FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️ FAISS non disponible. Installation: pip install faiss-cpu")

# Import conditionnel pour SentenceTransformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ SentenceTransformers non disponible. Installation: pip install sentence-transformers")

# Import de la config - CORRIGÉ
try:
    from core.config import (
        FAISS_INDEX_PATH,
        METADATA_PATH,
        EMBEDDING_MODEL,
        TOP_K,
        SIMILARITY_THRESHOLD
    )
except ImportError as e:
    print(f"⚠️ Import partiel de config: {e}")
    # Valeurs par défaut de secours
    from pathlib import Path
    BASE_DIR = Path(__file__).parent.parent.parent / "My_project"
    DATA_DIR = BASE_DIR / "data"
    FAISS_INDEX_PATH = DATA_DIR / "index.faiss"
    METADATA_PATH = DATA_DIR / "index.pkl"
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    TOP_K = 5
    SIMILARITY_THRESHOLD = 0.2

# Configuration du logging
logger = logging.getLogger(__name__)


class VectorStore:
    """
    Gestionnaire de base vectorielle FAISS 
    Version robuste avec valeurs par défaut
    """
    
    def __init__(self):
        """Initialise le VectorStore"""
        self.index = None
        self.metadata = []
        self.embedding_model = None
        self.is_loaded = False
        
        # Configuration
        self.embedding_model_name = EMBEDDING_MODEL
        self.top_k = TOP_K
        self.similarity_threshold = SIMILARITY_THRESHOLD
        
        logger.info("📦 Initialisation VectorStore...")
        self._load_all()
    
    def _load_all(self) -> None:
        """Charge tous les composants"""
        try:
            self._load_embedding_model()
            self._load_faiss_index()
            self._load_metadata()
            
            self.is_loaded = True
            logger.info(f"✅ VectorStore chargé - {len(self.metadata)} documents")
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement VectorStore: {e}")
            raise
    
    def _load_embedding_model(self) -> None:
        """Charge le modèle d'embedding"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("SentenceTransformers requis")
        
        logger.info(f"⏳ Chargement modèle: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        logger.info(f"✅ Modèle chargé: {self.embedding_model_name}")
    
    def _load_faiss_index(self) -> None:
        """Charge l'index FAISS"""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS requis")
        
        if not FAISS_INDEX_PATH.exists():
            raise FileNotFoundError(f"Index FAISS introuvable: {FAISS_INDEX_PATH}")
        
        self.index = faiss.read_index(str(FAISS_INDEX_PATH))
        logger.info(f"✅ Index FAISS chargé: {self.index.ntotal} vecteurs")
    
    def _load_metadata(self) -> None:
        """Charge les métadonnées"""
        if not METADATA_PATH.exists():
            raise FileNotFoundError(f"Métadonnées introuvables: {METADATA_PATH}")
        
        with open(METADATA_PATH, 'rb') as f:
            self.metadata = pickle.load(f)
        
        logger.info(f"✅ Métadonnées chargées: {len(self.metadata)} éléments")
        
        # Vérification cohérence
        if len(self.metadata) != self.index.ntotal:
            logger.warning(f"⚠️ Incohérence: {self.index.ntotal} vecteurs vs {len(self.metadata)} métadonnées")
    
    def encode_query(self, query: str) -> np.ndarray:
        """Encode une requête en vecteur"""
        if not self.is_loaded:
            raise RuntimeError("VectorStore non chargé")
        
        if not query or not query.strip():
            raise ValueError("Requête vide")
        
        embedding = self.embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
        return embedding.astype('float32')
    
    def search(self, query: str, k: int = None, score_threshold: float = None) -> List[Dict[str, Any]]:
        """Recherche les documents similaires"""
        if not self.is_loaded:
            raise RuntimeError("VectorStore non chargé")
        
        k = k or self.top_k
        score_threshold = score_threshold or self.similarity_threshold
        k = min(k, self.index.ntotal)
        
        try:
            query_vector = self.encode_query(query)
            distances, indices = self.index.search(query_vector, k)
            
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                
                similarity = 1.0 - (distance ** 2) / 2.0
                similarity = max(0.0, min(1.0, similarity))
                
                if similarity < score_threshold:
                    continue
                
                doc_data = self.metadata[idx]
                
                document = {
                    'content': doc_data.get('contenu', ''),
                    'source': doc_data.get('source', ''),
                    'type_document': doc_data.get('type_document', ''),
                    'norme': doc_data.get('norme', ''),
                    'article': doc_data.get('article', ''),
                    'similarity_score': float(similarity),
                    'distance_l2': float(distance),
                    'rank': i + 1,
                    'metadata': doc_data
                }
                results.append(document)
            
            logger.info(f"🔍 '{query}' -> {len(results)} résultats")
            return results
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return []
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Retourne TOUS les documents du VectorStore"""
        if not self.is_loaded:
            logger.warning("⚠️ VectorStore non chargé")
            return []
        
        try:
            all_docs = []
            
            for i, doc_data in enumerate(self.metadata):
                contenu = doc_data.get('contenu', '')
                content = doc_data.get('content', '')
                texte = doc_data.get('texte', '')
                phrase = doc_data.get('phrase', '')
                
                texte_principal = contenu or content or texte or phrase
                
                if not texte_principal:
                    continue
                
                document = {
                    'content': texte_principal,
                    'source': doc_data.get('source', ''),
                    'type_document': doc_data.get('type_document', ''),
                    'norme': doc_data.get('norme', ''),
                    'article': doc_data.get('article', ''),
                    'similarity_score': 1.0,
                    'id': i,
                    'metadata': doc_data
                }
                all_docs.append(document)
            
            logger.info(f"📥 {len(all_docs)} documents chargés")
            return all_docs
            
        except Exception as e:
            logger.error(f"❌ Erreur get_all_documents: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques"""
        if not self.is_loaded:
            return {"error": "Non chargé"}
        
        return {
            "total_vectors": self.index.ntotal,
            "total_metadata": len(self.metadata),
            "dimension": self.index.d,
            "model": self.embedding_model_name,
            "is_loaded": self.is_loaded
        }
    
    def health_check(self) -> bool:
        """Vérification de santé"""
        try:
            if not self.is_loaded:
                return False
            test_results = self.search("test", k=1)
            return True
        except Exception:
            return False


# Singleton
_vector_store_instance = None

def get_vector_store() -> VectorStore:
    """Retourne l'instance singleton du VectorStore"""
    global _vector_store_instance
    
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    
    return _vector_store_instance


def search_documents(query: str, k: int = None) -> List[Dict[str, Any]]:
    """Recherche rapide de documents"""
    return get_vector_store().search(query, k)

def get_vector_store_stats() -> Dict[str, Any]:
    """Statistiques rapides"""
    return get_vector_store().get_stats()
