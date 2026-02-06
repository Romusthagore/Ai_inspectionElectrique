# script/autocomplete_engine.py
#!/usr/bin/env python3
"""
Module d'auto-complétion pour l'application
"""

import logging
import pickle
import json
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class TrieNode:
    """Nœud pour l'arbre de recherche (Trie)"""
    def __init__(self):
        self.children = defaultdict(TrieNode)
        self.is_end = False
        self.prescriptions = []  # IDs des prescriptions terminant ici
        self.popularity = 0


class AutoCompleteEngine:
    """Moteur d'auto-complétion basé sur Trie"""
    
    def __init__(self):
        self.root = TrieNode()
        self.prescriptions_dict = {}
        self.loaded = False
        
    def build_from_prescriptions(self, prescriptions: List[Dict[str, Any]]):
        """Construit l'index à partir des prescriptions"""
        logger.info(f"🔨 Construction de l'index pour {len(prescriptions)} prescriptions")
        
        # Stocke les prescriptions
        self.prescriptions_dict = {p['id']: p for p in prescriptions}
        
        # Construit le Trie
        for prescription in prescriptions:
            # Index par texte complet (minuscules)
            text = prescription['action']['full_text'].lower()
            self._insert_text(text, prescription['id'])
            
            # Index par mots-clés
            for word in text.split():
                if len(word) > 2:  # Indexer seulement les mots de plus de 2 lettres
                    self._insert_word(word, prescription['id'])
            
            # Index par thème
            theme = prescription.get('theme', '').lower()
            if theme:
                self._insert_word(theme, prescription['id'])
        
        self.loaded = True
        logger.info("✅ Index d'auto-complétion construit")
    
    def _insert_text(self, text: str, prescription_id: str):
        """Insère un texte dans le Trie"""
        node = self.root
        for char in text:
            node = node.children[char]
        node.is_end = True
        if prescription_id not in node.prescriptions:
            node.prescriptions.append(prescription_id)
        node.popularity += 1
    
    def _insert_word(self, word: str, prescription_id: str):
        """Insère un mot isolé"""
        if len(word) < 3:
            return
        self._insert_text(word, prescription_id)
    
    def get_suggestions(self, prefix: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Retourne les suggestions pour un préfixe"""
        if not self.loaded or not prefix:
            return []
        
        prefix = prefix.lower()
        
        # Trouve le nœud correspondant au préfixe
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        
        # Collecte toutes les suggestions
        suggestions = []
        self._collect_from_node(node, prefix, suggestions)
        
        # Trie par pertinence
        suggestions.sort(key=lambda x: (
            -x['popularity'],  # Popularité d'abord
            -x['relevance'],   # Puis pertinence
            len(x['text'])     # Puis longueur
        ))
        
        return suggestions[:max_results]
    
    def _collect_from_node(self, node: TrieNode, current_prefix: str, results: List):
        """Collecte récursivement les suggestions"""
        if node.is_end:
            for pid in node.prescriptions:
                prescription = self.prescriptions_dict.get(pid)
                if prescription:
                    results.append({
                        'id': pid,
                        'text': prescription['action']['full_text'],
                        'theme': prescription.get('theme', ''),
                        'popularity': node.popularity,
                        'relevance': self._calculate_relevance(current_prefix, prescription)
                    })
        
        for char, child_node in node.children.items():
            self._collect_from_node(child_node, current_prefix + char, results)
    
    def _calculate_relevance(self, prefix: str, prescription: Dict) -> float:
        """Calcule la pertinence d'une suggestion"""
        text = prescription['action']['full_text'].lower()
        theme = prescription.get('theme', '').lower()
        
        score = 0.0
        
        # Bonus pour correspondance exacte au début
        if text.startswith(prefix):
            score += 10.0
        
        # Bonus pour correspondance au début d'un mot
        words = text.split()
        for word in words:
            if word.startswith(prefix):
                score += 5.0
                break
        
        # Bonus pour thème correspondant
        if prefix in theme:
            score += 3.0
        
        # Pénalité pour longueur
        score -= len(text) * 0.01
        
        return score
    
    def save_index(self, filepath: str):
        """Sauvegarde l'index sur disque"""
        with open(filepath, 'wb') as f:
            pickle.dump((self.root, self.prescriptions_dict), f)
        logger.info(f"💾 Index sauvegardé : {filepath}")
    
    def load_index(self, filepath: str):
        """Charge l'index depuis le disque"""
        try:
            with open(filepath, 'rb') as f:
                self.root, self.prescriptions_dict = pickle.load(f)
            self.loaded = True
            logger.info(f"📂 Index chargé : {filepath}")
        except Exception as e:
            logger.error(f"❌ Erreur chargement index : {e}")


class EnhancedSuggestionManager:
    """
    Gestionnaire unifié pour l'auto-complétion et suggestions de normes
    """
    
    def __init__(self):
        self.autocomplete_engine = AutoCompleteEngine()
        
        # Cache pour les suggestions
        self.suggestion_cache = {}
        self.cache_size = 100
        
        logger.info("✅ EnhancedSuggestionManager initialisé")
    
    def get_autocomplete_suggestions(self, prefix: str) -> List[str]:
        """
        Retourne des suggestions d'auto-complétion RAPIDES
        """
        if not prefix or len(prefix) < 2:
            return []
        
        # Vérifie le cache
        cache_key = prefix.lower()
        if cache_key in self.suggestion_cache:
            return self.suggestion_cache[cache_key]
        
        # Récupère suggestions du Trie
        suggestions = self.autocomplete_engine.get_suggestions(prefix, max_results=5)
        
        # Format pour l'affichage
        formatted = [sug['text'] for sug in suggestions[:5]]
        
        # Met en cache
        self.suggestion_cache[cache_key] = formatted
        
        # Gestion du cache (FIFO)
        if len(self.suggestion_cache) > self.cache_size:
            oldest_key = next(iter(self.suggestion_cache))
            del self.suggestion_cache[oldest_key]
        
        return formatted
    
    def validate_and_suggest_norms(self, text: str) -> Tuple[Optional[Dict], List[Dict]]:
        """
        Valide un texte et suggère des normes associées
        """
        # Cherche la prescription la plus proche
        best_match = None
        best_score = 0
        
        for prescription in self.autocomplete_engine.prescriptions_dict.values():
            prescription_text = prescription['action']['full_text'].lower()
            text_lower = text.lower()
            
            # Calcule la similarité
            similarity = SequenceMatcher(None, text_lower, prescription_text).ratio()
            
            if similarity > best_score and similarity > 0.7:  # Seuil de similarité
                best_score = similarity
                best_match = prescription
        
        # Si trouvé, suggère des normes (version simplifiée)
        if best_match:
            norm_suggestions = [
                {'reference': 'NFC 15-100 Article 411.3.3', 'confidence': 0.8},
                {'reference': 'NF C 15-100 § 531', 'confidence': 0.7},
                {'reference': 'R.4226-12', 'confidence': 0.6}
            ]
            return best_match, norm_suggestions
        
        return None, []
    
    def load_prescriptions_from_file(self, filepath: str):
        """Charge les prescriptions depuis un fichier JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                prescriptions = json.load(f)
            
            # Formatte les prescriptions
            formatted_prescriptions = []
            for p in prescriptions:
                formatted_prescriptions.append({
                    'id': p.get('id', 'unknown'),
                    'action': {
                        'full_text': p.get('contenu', p.get('text', ''))
                    },
                    'theme': p.get('Thème', p.get('theme', ''))
                })
            
            # Construit l'index
            self.autocomplete_engine.build_from_prescriptions(formatted_prescriptions)
            logger.info(f"✅ {len(formatted_prescriptions)} prescriptions chargées")
            
            return True
        except Exception as e:
            logger.error(f"❌ Erreur chargement prescriptions : {e}")
            return False


def create_suggestion_manager(prescriptions_file: str = None) -> EnhancedSuggestionManager:
    """Factory function pour créer le gestionnaire de suggestions"""
    manager = EnhancedSuggestionManager()
    
    # Charge les prescriptions si fichier fourni
    if prescriptions_file:
        manager.load_prescriptions_from_file(prescriptions_file)
    
    return manager


# Instance globale (optionnel)
autocomplete_engine = AutoCompleteEngine()


if __name__ == "__main__":
    print("✅ Module AutoCompleteEngine chargé")
    print("📋 Fonctionnalités :")
    print("  - Auto-complétion en temps réel")
    print("  - Suggestions de normes")
    print("  - Gestionnaire unifié")