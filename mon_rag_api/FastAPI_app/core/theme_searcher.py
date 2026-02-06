#!/usr/bin/env python3
"""
ThemeSearcher - Module de recherche floue par thème
Version complète et testée
"""

import logging
import re
import unicodedata
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ThemeSearcher:
    """
    Moteur de recherche floue par thème
    Supporte les expressions partielles : 'éclai' → 'Éclairage'
    """
    
    def __init__(self, vectorstore=None, documents: List[Dict] = None):
        """
        Initialise avec soit un VectorStore, soit une liste de documents
        
        Args:
            vectorstore: VectorStore personnalisé (optionnel)
            documents: Liste de documents avec champ 'Thème' (optionnel)
        """
        self.vectorstore = vectorstore
        self.documents = documents or []
        
        # Index des thèmes
        self.themes_index = {}  # thème_normalise -> thème_original
        self.docs_by_theme = defaultdict(list)  # thème -> [documents]
        
        # Cache pour performance
        self._cache_matches = {}
        
        # Charger les documents
        self._load_documents()
        
        logger.info(f"✅ ThemeSearcher initialisé: {len(self.themes_index)} thèmes uniques")
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour la recherche insensible"""
        if not text:
            return ""
        
        # Minuscules
        text = text.lower()
        
        # Supprimer les accents
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        
        # Nettoyer
        text = re.sub(r'[^\w\s-]', '', text)
        return text.strip()
    
    def _load_documents(self):
        """Charge et indexe les documents"""
        try:
            # 1. Priorité : liste de documents directe
            if self.documents:
                all_docs = self.documents
            
            # 2. Sinon, depuis vectorstore
            elif self.vectorstore:
                if hasattr(self.vectorstore, 'documents'):
                    all_docs = self.vectorstore.documents
                elif hasattr(self.vectorstore, 'get_all_documents'):
                    all_docs = self.vectorstore.get_all_documents()
                else:
                    logger.warning("⚠️ VectorStore sans accès direct aux documents")
                    all_docs = []
            else:
                all_docs = []
            
            # Indexer les thèmes
            theme_count = 0
            for doc in all_docs:
                theme = self._extract_theme(doc)
                if theme:
                    theme_norm = self._normalize_text(theme)
                    theme_original = theme
                    
                    self.themes_index[theme_norm] = theme_original
                    self.docs_by_theme[theme_original].append(doc)
                    theme_count += 1
            
            logger.info(f"📊 {theme_count} documents indexés par thème")
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement ThemeSearcher: {e}")
    
    def _extract_theme(self, doc: Dict) -> Optional[str]:
        """Extrait le thème d'un document"""
        # Chercher dans différents champs possibles
        for field in ['Thème', 'theme', 'category', 'categorie', 'type', 'domaine']:
            if field in doc and doc[field]:
                theme = str(doc[field]).strip()
                if theme:
                    return theme
        
        return None
    
    def search_themes(self, query: str, min_similarity: float = 0.5) -> List[str]:
        """
        Recherche les thèmes correspondant à une expression
        
        Args:
            query: Expression de recherche (ex: "éclai", "câble", "protect")
            min_similarity: Seuil de similarité (0.0 à 1.0)
        
        Returns:
            Liste des thèmes triés par pertinence
        """
        if not query:
            return []
        
        # Vérifier le cache
        cache_key = f"{query}_{min_similarity}"
        if cache_key in self._cache_matches:
            return self._cache_matches[cache_key]
        
        query_norm = self._normalize_text(query)
        
        matches_with_scores = []
        
        for theme_norm, theme_original in self.themes_index.items():
            # 1. Inclusion directe (score élevé)
            if query_norm in theme_norm:
                matches_with_scores.append((theme_original, 1.0))
                continue
            
            # 2. Inclusion inverse
            if theme_norm in query_norm:
                matches_with_scores.append((theme_original, 0.8))
                continue
            
            # 3. Similarité floue
            similarity = SequenceMatcher(None, query_norm, theme_norm).ratio()
            
            # Bonus pour préfixes
            if len(query_norm) >= 3 and theme_norm.startswith(query_norm):
                similarity = max(similarity, 0.85)
            
            if similarity >= min_similarity:
                matches_with_scores.append((theme_original, similarity))
        
        # Trier par score
        matches_with_scores.sort(key=lambda x: x[1], reverse=True)
        matches = [theme for theme, _ in matches_with_scores]
        
        # Mettre en cache
        self._cache_matches[cache_key] = matches
        
        return matches
    
    def get_theme_documents(self, theme: str, max_docs: int = 20) -> List[Dict]:
        """
        Récupère tous les documents d'un thème spécifique
        
        Args:
            theme: Thème exact (ex: "Éclairage")
            max_docs: Nombre maximum de documents
        
        Returns:
            Liste des documents du thème
        """
        return self.docs_by_theme.get(theme, [])[:max_docs]
    
    def search_documents_by_theme_expression(
        self, 
        theme_expression: str, 
        max_docs: int = 20
    ) -> List[Dict]:
        """
        Recherche des documents par expression de thème
        
        Args:
            theme_expression: Expression partielle (ex: "éclai", "câble")
            max_docs: Nombre maximum de documents
        
        Returns:
            Liste des documents des thèmes correspondants
        """
        matching_themes = self.search_themes(theme_expression)
        
        if not matching_themes:
            return []
        
        # Collecter tous les documents des thèmes correspondants
        all_docs = []
        for theme in matching_themes:
            all_docs.extend(self.docs_by_theme.get(theme, []))
        
        return all_docs[:max_docs]
    
    def get_available_themes(self) -> List[str]:
        """Retourne la liste de tous les thèmes disponibles"""
        return sorted(self.docs_by_theme.keys())
    
    def get_theme_stats(self) -> Dict[str, int]:
        """Retourne les statistiques par thème"""
        return {theme: len(docs) for theme, docs in self.docs_by_theme.items()}
    
    def suggest_themes(self, partial_query: str, max_suggestions: int = 5) -> List[str]:
        """
        Suggère des thèmes complets pour l'autocomplétion
        
        Args:
            partial_query: Début de thème (ex: "écl")
            max_suggestions: Nombre maximum de suggestions
        
        Returns:
            Liste des suggestions formatées
        """
        matches = self.search_themes(partial_query)
        
        suggestions = []
        for theme in matches[:max_suggestions]:
            doc_count = len(self.docs_by_theme.get(theme, []))
            
            if doc_count > 0:
                suggestion = f"{theme} ({doc_count} documents)"
            else:
                suggestion = theme
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def is_theme_available(self, theme: str) -> bool:
        """Vérifie si un thème existe dans la base"""
        return theme in self.docs_by_theme


def get_theme_searcher(vectorstore=None, documents: List[Dict] = None) -> ThemeSearcher:
    """
    Factory function pour créer un ThemeSearcher
    
    Args:
        vectorstore: VectorStore personnalisé
        documents: Liste de documents alternative
    
    Returns:
        Instance de ThemeSearcher
    """
    return ThemeSearcher(vectorstore=vectorstore, documents=documents)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("🧪 TESTS ThemeSearcher")
    print("=" * 50)
    
    # Données de test
    test_documents = [
        {"id": 1, "content": "prévoir un éclairage de sécurité", "Thème": "Éclairage"},
        {"id": 2, "content": "installer un dispositif de protection", "Thème": "Protection"},
        {"id": 3, "content": "disjoncteur différentiel 30mA", "Thème": "Protection différentielle"},
        {"id": 4, "content": "mise à la terre des masses", "Thème": "Mise à la terre"},
        {"id": 5, "content": "section des câbles", "Thème": "Câblage"},
        {"id": 6, "content": "prises 16A", "Thème": "Prises"},
    ]
    
    # Créer le searcher
    searcher = ThemeSearcher(documents=test_documents)
    
    print(f"📊 Thèmes disponibles: {searcher.get_available_themes()}")
    
    # Tests de recherche
    test_cases = [
        ("éclai", ["Éclairage"]),
        ("protect", ["Protection", "Protection différentielle"]),
        ("terre", ["Mise à la terre"]),
        ("câble", ["Câblage"]),
        ("prise", ["Prises"]),
    ]
    
    print("\n🔍 Tests de recherche:")
    for query, expected in test_cases:
        matches = searcher.search_themes(query)
        status = "✅" if matches else "❌"
        print(f"{status} '{query}' → {matches}")
    
    # Tests de suggestions
    print("\n💡 Tests de suggestions:")
    suggestions_tests = ["écl", "prot", "câb"]
    for query in suggestions_tests:
        suggestions = searcher.suggest_themes(query, 2)
        print(f"'{query}' → {suggestions}")
    
    print("\n" + "=" * 50)
    print("✅ ThemeSearcher testé avec succès!")