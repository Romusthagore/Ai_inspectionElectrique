#!/usr/bin/env python3
"""
Parser de réponses LLM pour extraction structurée
Gère les formats JSON, Markdown et texte libre
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parser intelligent pour extraire des données structurées des réponses LLM
    Supporte JSON, Markdown structuré et texte libre
    """
    
    # Patterns de reconnaissance
    PATTERNS = {
        'json_with_backticks': r'```json\s*(.*?)\s*```',
        'json_raw': r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        'references': r'(NF\s*C\s*\d+[-\d]*|Article\s+\d+[.\d]*|UTE\s*C\s*\d+[-\d]*)',
        'gravite_critique': r'\b(critique|danger|mortel|électrocution|incendie)\b',
        'gravite_majeur': r'\b(majeur|grave|important|sérieux)\b',
        'gravite_mineur': r'\b(mineur|léger|amélioration)\b',
        'delai_immediat': r'\b(immédiat|urgence|urgent)\b',
        'delai_30j': r'\b(30\s*jours?|1\s*mois)\b',
        'delai_90j': r'\b(90\s*jours?|3\s*mois)\b',
    }
    
    # Localisations standards
    LOCALISATIONS = [
        'cuisine', 'salle de bain', 'chambre', 'salon', 'séjour',
        'tableau électrique', 'garage', 'couloir', 'buanderie', 
        'cave', 'combles', 'extérieur', 'entrée', 'bureau',
        'sous-sol', 'grenier', 'véranda', 'terrasse'
    ]
    
    def __init__(self):
        """Initialise le parser"""
        logger.info("✅ ResponseParser initialisé")
    
    def parse(self, response_text: str, format_type: str = "auto") -> Dict[str, Any]:
        """
        Parse une réponse LLM et extrait les données structurées
        
        Args:
            response_text: Texte de la réponse LLM
            format_type: Type de format attendu ("json", "markdown", "text", "auto")
            
        Returns:
            Dictionnaire structuré avec les données extraites
        """
        try:
            logger.info(f"🔄 Parsing réponse (format: {format_type})")
            
            # Nettoyage initial
            response_clean = self._clean_response(response_text)
            
            # Détection automatique du format
            if format_type == "auto":
                format_type = self._detect_format(response_clean)
            
            # Parsing selon le format
            if format_type == "json":
                result = self._parse_json(response_clean)
            elif format_type == "markdown":
                result = self._parse_markdown(response_clean)
            else:
                result = self._parse_text(response_clean)
            
            # Validation et complétion
            result = self._validate_and_complete(result)
            
            logger.info(f"✅ Parsing réussi (gravité: {result['niveau_gravite']})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur parsing: {e}", exc_info=True)
            return self._default_result(response_text)
    
    def _clean_response(self, text: str) -> str:
        """Nettoie le texte de la réponse"""
        # Supprimer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        # Supprimer les retours à la ligne multiples
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def _detect_format(self, text: str) -> str:
        """Détecte automatiquement le format de la réponse"""
        # Rechercher du JSON
        if re.search(self.PATTERNS['json_with_backticks'], text, re.DOTALL):
            return "json"
        if re.search(self.PATTERNS['json_raw'], text, re.DOTALL):
            return "json"
        
        # Rechercher du Markdown structuré
        if re.search(r'\*\*[A-Z\s]+\*\*\s*:', text):
            return "markdown"
        
        return "text"
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """
        Parse une réponse JSON
        """
        # Essayer avec backticks
        json_match = re.search(self.PATTERNS['json_with_backticks'], text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON avec backticks invalide: {e}")
        
        # Essayer sans backticks
        json_match = re.search(self.PATTERNS['json_raw'], text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON brut invalide: {e}")
        
        # Si échec, passer au parsing texte
        logger.warning("⚠️ Aucun JSON valide trouvé, fallback vers parsing texte")
        return self._parse_text(text)
    
    def _parse_markdown(self, text: str) -> Dict[str, Any]:
        """
        Parse une réponse en Markdown structuré
        Format attendu:
        **OBSERVATION CORRIGÉE**: texte
        **RÉFÉRENCES**: ref1, ref2
        etc.
        """
        result = self._default_structure()
        
        # Extraire les sections Markdown
        sections = {
            'observation_corrigee': r'\*\*(?:OBSERVATION\s*CORRIGÉE?|OBSERVATION)\*\*\s*:\s*([^\n*]+)',
            'references_normatives': r'\*\*(?:RÉFÉRENCES?|REFS?)\*\*\s*:\s*([^\n*]+)',
            'niveau_gravite': r'\*\*(?:GRAVITÉ|NIVEAU)\*\*\s*:\s*([^\n*]+)',
            'risques_identifies': r'\*\*(?:RISQUES?)\*\*\s*:\s*([^\n*]+)',
            'actions_correctives': r'\*\*(?:ACTIONS?|CORRECTIONS?)\*\*\s*:\s*([^\n*]+)',
            'delai_recommande': r'\*\*(?:DÉLAI|DEADLINE)\*\*\s*:\s*([^\n*]+)',
            'localisation': r'\*\*(?:LOCALISATION|LIEU)\*\*\s*:\s*([^\n*]+)',
        }
        
        for field, pattern in sections.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                if field == 'references_normatives':
                    # Séparer les références multiples
                    result[field] = [ref.strip() for ref in re.split(r'[,;]', value) if ref.strip()]
                elif field == 'risques_identifies':
                    result[field] = [r.strip() for r in re.split(r'[,;]', value) if r.strip()]
                elif field == 'actions_correctives':
                    result[field] = [a.strip() for a in re.split(r'[,;]', value) if a.strip()]
                else:
                    result[field] = value
        
        return result
    
    def _parse_text(self, text: str) -> Dict[str, Any]:
        """
        Parse du texte libre avec extraction intelligente
        """
        result = self._default_structure()
        
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        texte_complet = ' '.join(lines)
        texte_lower = texte_complet.lower()
        
        # 1. Observation corrigée (première phrase significative)
        for line in lines:
            # Ignorer les lignes de titre ou très courtes
            if len(line) > 20 and not line.startswith(('#', '**', '-', '*')):
                result['observation_corrigee'] = line
                break
        
        # Si pas trouvé, prendre les 200 premiers caractères
        if not result['observation_corrigee']:
            result['observation_corrigee'] = texte_complet[:200]
        
        # 2. Niveau de gravité
        result['niveau_gravite'] = self._extract_gravite(texte_lower)
        
        # 3. Références normatives
        refs = re.findall(self.PATTERNS['references'], texte_complet, re.IGNORECASE)
        result['references_normatives'] = list(dict.fromkeys(refs[:5]))  # Unique, max 5
        
        # 4. Risques identifiés
        result['risques_identifies'] = self._extract_risques(texte_complet)
        
        # 5. Actions correctives
        result['actions_correctives'] = self._extract_actions(texte_complet)
        
        # 6. Délai recommandé
        result['delai_recommande'] = self._extract_delai(texte_lower)
        
        # 7. Localisation
        result['localisation'] = self._extract_localisation(texte_lower)
        
        return result
    
    def _extract_gravite(self, text_lower: str) -> str:
        """Extrait le niveau de gravité du texte"""
        if re.search(self.PATTERNS['gravite_critique'], text_lower):
            return "Critique"
        elif re.search(self.PATTERNS['gravite_majeur'], text_lower):
            return "Majeur"
        elif re.search(self.PATTERNS['gravite_mineur'], text_lower):
            return "Mineur"
        return "Mineur"
    
    def _extract_risques(self, text: str) -> List[str]:
        """Extrait les risques identifiés"""
        risques = []
        
        patterns = [
            r'risque[s]?\s*:\s*([^.\n]+)',
            r'danger[s]?\s*:\s*([^.\n]+)',
            r'peut\s+(?:causer|provoquer|entraîner)\s+([^.\n]+)',
            r'électrocution',
            r'incendie',
            r'court-circuit',
            r'surtension',
            r'défaut\s+(?:d\'isolement|de\s+mise\s+à\s+la\s+terre)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            risques.extend([m.strip() for m in matches if isinstance(m, str)])
        
        # Nettoyer et dédupliquer
        risques = list(dict.fromkeys([r for r in risques if len(r) > 5]))
        
        # Ajouter des risques standards si vide
        if not risques:
            risques = ["Risque électrique à évaluer", "Non-conformité normative"]
        
        return risques[:5]  # Max 5 risques
    
    def _extract_actions(self, text: str) -> List[str]:
        """Extrait les actions correctives"""
        actions = []
        
        patterns = [
            r'action[s]?\s*(?:corrective[s]?)?\s*:\s*([^.\n]+)',
            r'corriger\s+([^.\n]+)',
            r'installer\s+([^.\n]+)',
            r'remplacer\s+([^.\n]+)',
            r'vérifier\s+([^.\n]+)',
            r'mettre\s+en\s+conformité\s+([^.\n]+)',
            r'reprendre\s+([^.\n]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            actions.extend([m.strip() for m in matches if isinstance(m, str)])
        
        # Nettoyer et dédupliquer
        actions = list(dict.fromkeys([a for a in actions if len(a) > 5]))
        
        # Ajouter une action standard si vide
        if not actions:
            actions = ["Mise en conformité avec la NFC 15-100", "Vérification par un électricien qualifié"]
        
        return actions[:5]  # Max 5 actions
    
    def _extract_delai(self, text_lower: str) -> str:
        """Extrait le délai recommandé"""
        if re.search(self.PATTERNS['delai_immediat'], text_lower):
            return "immédiat"
        elif re.search(self.PATTERNS['delai_30j'], text_lower):
            return "30 jours"
        elif re.search(self.PATTERNS['delai_90j'], text_lower):
            return "90 jours"
        return "30 jours"  # Défaut
    
    def _extract_localisation(self, text_lower: str) -> str:
        """Extrait la localisation"""
        for loc in self.LOCALISATIONS:
            if loc.lower() in text_lower:
                return loc.capitalize()
        return "non spécifiée"
    
    def _default_structure(self) -> Dict[str, Any]:
        """Retourne la structure par défaut"""
        return {
            "observation_corrigee": "",
            "references_normatives": [],
            "niveau_gravite": "Mineur",
            "risques_identifies": [],
            "actions_correctives": [],
            "delai_recommande": "30 jours",
            "localisation": "non spécifiée"
        }
    
    def _validate_and_complete(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide et complète les champs obligatoires
        """
        default = self._default_structure()
        
        # Compléter les champs manquants
        for key, default_value in default.items():
            if key not in result or not result[key]:
                result[key] = default_value
        
        # Normaliser le niveau de gravité
        if result['niveau_gravite'] not in ['Critique', 'Majeur', 'Mineur']:
            result['niveau_gravite'] = 'Mineur'
        
        # Normaliser le délai
        if result['delai_recommande'] not in ['immédiat', '30 jours', '90 jours']:
            result['delai_recommande'] = '30 jours'
        
        # S'assurer que les listes ne sont pas vides
        if not result['references_normatives']:
            result['references_normatives'] = ['NFC 15-100 (vérification requise)']
        
        if not result['risques_identifies']:
            result['risques_identifies'] = ['Risque électrique à évaluer']
        
        if not result['actions_correctives']:
            result['actions_correctives'] = ['Mise en conformité nécessaire']
        
        return result
    
    def _default_result(self, original_text: str) -> Dict[str, Any]:
        """Résultat par défaut en cas d'erreur"""
        return {
            "observation_corrigee": original_text[:200] if original_text else "Erreur de parsing",
            "references_normatives": ["NFC 15-100"],
            "niveau_gravite": "Mineur",
            "risques_identifies": ["Analyse impossible"],
            "actions_correctives": ["Vérification manuelle requise"],
            "delai_recommande": "30 jours",
            "localisation": "non spécifiée",
            "parsing_error": True
        }
    
    def parse_batch(self, responses: List[str]) -> List[Dict[str, Any]]:
        """
        Parse un lot de réponses
        
        Args:
            responses: Liste de réponses à parser
            
        Returns:
            Liste de résultats structurés
        """
        results = []
        
        for i, response in enumerate(responses, 1):
            logger.info(f"📋 Parsing réponse {i}/{len(responses)}")
            result = self.parse(response)
            result['batch_index'] = i
            results.append(result)
        
        return results
    
    def export_to_json(self, result: Union[Dict, List[Dict]], 
                      filepath: str = "parsed_results.json"):
        """
        Exporte les résultats en JSON
        
        Args:
            result: Résultat(s) à exporter
            filepath: Chemin du fichier de sortie
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Résultats exportés: {filepath}")
        except Exception as e:
            logger.error(f"❌ Erreur export: {e}")


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

_parser_instance = None

def get_response_parser() -> ResponseParser:
    """Retourne l'instance singleton du parser"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = ResponseParser()
    return _parser_instance

def parse_llm_response(response_text: str, format_type: str = "auto") -> Dict[str, Any]:
    """Fonction rapide pour parser une réponse"""
    parser = get_response_parser()
    return parser.parse(response_text, format_type)


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("🧪 TEST RESPONSE PARSER")
    print("=" * 70)
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = get_response_parser()
    
    # Test 1: Réponse JSON
    print("\n📋 TEST 1: Parsing JSON")
    print("-" * 70)
    
    json_response = """
    ```json
    {
      "observation_corrigee": "Absence de dispositif différentiel 30mA dans le circuit cuisine",
      "references_normatives": ["NFC 15-100 Article 55.1", "NFC 15-100 Article 411.3.3"],
      "niveau_gravite": "Critique",
      "risques_identifies": ["Électrocution", "Incendie"],
      "actions_correctives": ["Installer DDR 30mA Type A", "Vérifier mise à la terre"],
      "delai_recommande": "immédiat",
      "localisation": "Cuisine"
    }
    ```
    """
    
    result1 = parser.parse(json_response)
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    
    # Test 2: Réponse Markdown
    print("\n📋 TEST 2: Parsing Markdown")
    print("-" * 70)
    
    markdown_response = """
    **OBSERVATION CORRIGÉE**: Câble de section insuffisante sur le circuit chauffage
    **RÉFÉRENCES**: NFC 15-100 Article 52.1, UTE C 15-105
    **GRAVITÉ**: Majeur
    **RISQUES**: Échauffement du câble, risque d'incendie
    **ACTIONS**: Remplacer le câble par section 2.5mm², vérifier protection
    **DÉLAI**: 30 jours
    **LOCALISATION**: Salon
    """
    
    result2 = parser.parse(markdown_response)
    print(json.dumps(result2, indent=2, ensure_ascii=False))
    
    # Test 3: Texte libre
    print("\n📋 TEST 3: Parsing texte libre")
    print("-" * 70)
    
    text_response = """
    Le tableau électrique est encombré et ne respecte pas les distances de sécurité.
    Selon l'article 55 de la NFC 15-100, un espace libre doit être maintenu.
    C'est un problème majeur qui peut causer des difficultés d'intervention.
    Il faut dégager l'espace et réorganiser le tableau immédiatement.
    Localisation: garage principal.
    """
    
    result3 = parser.parse(text_response)
    print(json.dumps(result3, indent=2, ensure_ascii=False))
    
    # Test 4: Batch parsing
    print("\n📋 TEST 4: Parsing en lot")
    print("-" * 70)
    
    batch_responses = [json_response, markdown_response, text_response]
    batch_results = parser.parse_batch(batch_responses)
    
    print(f"✅ {len(batch_results)} réponses parsées")
    
    # Export
    parser.export_to_json(batch_results, "test_parsing_batch.json")
    
    print("\n" + "=" * 70)
    print("🎯 RESPONSE PARSER OPÉRATIONNEL !")
    print("   ✅ Supporte JSON, Markdown et texte libre")
    print("   ✅ Extraction intelligente des données")
    print("   ✅ Validation et complétion automatique")
    print("=" * 70)