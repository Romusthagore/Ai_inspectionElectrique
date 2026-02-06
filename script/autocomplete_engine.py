# script/autocomplete_engine.py
#!/usr/bin/env python3
"""
Module d'auto-complétion simplifié
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import os

logger = logging.getLogger(__name__)


class SimpleAutoCompleteEngine:
    """Moteur d'auto-complétion simplifié"""
    
    def __init__(self):
        self.suggestions_data = {}
        self.loaded = False
        logger.info("✅ SimpleAutoCompleteEngine initialisé")
    
    def load_from_file(self, filepath: str):
        """Charge les données depuis un fichier JSON"""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"⚠️ Fichier non trouvé: {filepath}")
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Prépare les données pour l'auto-complétion
            for item in data:
                text = item.get('contenu', item.get('text', ''))
                if text:
                    # Prend les 3 premiers caractères comme clé
                    prefix = text[:3].lower()
                    if prefix not in self.suggestions_data:
                        self.suggestions_data[prefix] = []
                    self.suggestions_data[prefix].append({
                        'id': item.get('id', ''),
                        'text': text,
                        'theme': item.get('Thème', item.get('theme', ''))
                    })
            
            self.loaded = True
            logger.info(f"✅ {len(data)} prescriptions chargées")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement: {e}")
            return False
    
    def get_suggestions(self, prefix: str, max_results: int = 5) -> List[str]:
        """Retourne des suggestions"""
        if not prefix or len(prefix) < 2:
            return []
        
        prefix_lower = prefix.lower()
        results = []
        
        # Recherche exacte par préfixe
        if prefix_lower[:3] in self.suggestions_data:
            for item in self.suggestions_data[prefix_lower[:3]]:
                if item['text'].lower().startswith(prefix_lower):
                    results.append(item['text'])
        
        # Recherche partielle si peu de résultats
        if len(results) < 3:
            for key, items in self.suggestions_data.items():
                if prefix_lower in key:
                    for item in items:
                        if item['text'] not in results:
                            results.append(item['text'])
        
        # Suggestions génériques si vide
        if not results:
            results = [
                f"{prefix} - Vérifier la conformité",
                f"{prefix} - Inspecter l'installation",
                f"{prefix} - Contrôler selon norme"
            ]
        
        return results[:max_results]


class EnhancedSuggestionManager:
    """Gestionnaire de suggestions simplifié"""
    
    def __init__(self, data_file: str = None):
        self.engine = SimpleAutoCompleteEngine()
        
        if data_file:
            self.load_data(data_file)
        else:
            # Données de test par défaut
            self.load_test_data()
        
        logger.info("✅ EnhancedSuggestionManager initialisé")
    
    def load_data(self, filepath: str):
        """Charge les données depuis un fichier"""
        return self.engine.load_from_file(filepath)
    
    def load_test_data(self):
        """Charge des données de test"""
        test_data = [
            {"id": "1", "contenu": "Remplacer le câble rigide par un souple", "Thème": "Câblage"},
            {"id": "2", "contenu": "Vérifier la protection différentielle 30mA", "Thème": "Protection"},
            {"id": "3", "contenu": "Contrôler la mise à la terre", "Thème": "Terre"},
            {"id": "4", "contenu": "Remplacer le DDR défectueux", "Thème": "Protection"},
            {"id": "5", "contenu": "Vérifier la section des câbles", "Thème": "Câblage"}
        ]
        
        for item in test_data:
            prefix = item['contenu'][:3].lower()
            if prefix not in self.engine.suggestions_data:
                self.engine.suggestions_data[prefix] = []
            self.engine.suggestions_data[prefix].append(item)
        
        self.engine.loaded = True
        logger.info("✅ Données de test chargées")
    
    def get_autocomplete_suggestions(self, prefix: str) -> List[str]:
        """Retourne des suggestions d'auto-complétion"""
        return self.engine.get_suggestions(prefix)
    
    def validate_and_suggest_norms(self, text: str) -> Tuple[Optional[Dict], List[Dict]]:
        """Valide un texte et suggère des normes"""
        logger.info(f"🔍 Validation de: {text}")
        
        # Cherche la prescription correspondante
        best_match = None
        for prefix, items in self.engine.suggestions_data.items():
            for item in items:
                if text.lower() in item['contenu'].lower():
                    best_match = item
                    break
            if best_match:
                break
        
        # Normes suggérées (simulées)
        normes = [
            {"reference": "NFC 15-100 Article 411.3.3", "confidence": 0.85, "type": "norme"},
            {"reference": "NF C 15-100 § 531", "confidence": 0.75, "type": "norme"},
            {"reference": "R.4226-12", "confidence": 0.65, "type": "règlement"}
        ]
        
        return best_match, normes


# Factory function
def create_suggestion_manager(data_file: str = None) -> EnhancedSuggestionManager:
    """Crée un gestionnaire de suggestions"""
    return EnhancedSuggestionManager(data_file)


if __name__ == "__main__":
    print("✅ Module AutoCompleteEngine chargé")
    print("📋 Fonctionnalités :")
    print("  - Auto-complétion simplifiée")
    print("  - Suggestions de normes")
    print("  - Gestionnaire intégré")