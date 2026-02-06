#!/usr/bin/env python3
"""
Module OrthographeCorrector - Correction orthographique rapide
Utilise le LLM configuré via config.py pour corriger fautes d'orthographe
"""

import logging
from typing import Dict, Any, List
import json
import re

# Import de la configuration
try:
    from config import get_llm_client, TEMPERATURE, logger as config_logger
except ImportError as e:
    print(f"❌ Erreur d'import config : {e}")
    raise

logger = logging.getLogger(__name__)


class OrthographeCorrector:
    """
    Correcteur orthographique léger utilisant LLM
    Corrige UNIQUEMENT l'orthographe, ne reformule PAS le sens
    """
    
    def __init__(self, temperature: float = 0.1):
        """
        Initialise le correcteur avec un LLM léger
        
        Args:
            temperature: Température basse pour cohérence (défaut: 0.1)
        """
        self.llm = get_llm_client(temperature=temperature)
        self.temperature = temperature
        
        # Prompt strict pour correction orthographique UNIQUEMENT
        self.prompt_template = self._get_prompt_template()
        
        # Cache pour éviter corrections multiples identiques
        self.cache = {}
        
        logger.info(f"✅ OrthographeCorrector initialisé (temp={temperature})")
    
    def _get_prompt_template(self) -> str:
        """Retourne le prompt pour correction orthographique STRICTE"""
        return """Tu es un correcteur orthographique STRICT.

RÈGLE ABSOLUE : Corrige UNIQUEMENT l'orthographe, la grammaire et la ponctuation.
NE CHANGE PAS le sens, NE REFORMULE PAS, N'AJOUTE RIEN.

Texte à corriger : "{texte_brut}"

EXEMPLES CORRECTS :
- Input: "le curant nominal" → Output: "le courant nominal"
- Input: "cable abimé" → Output: "câble abîmé"
- Input: "disjoncteur differanciel" → Output: "disjoncteur différentiel"
- Input: "prise pas terre" → Output: "prise pas terre" (on garde le sens même si maladroit)

EXEMPLES INTERDITS :
- Input: "le curant" → Output: "le courant alternatif traverse..." ❌ (REFORMULATION)
- Input: "cable" → Output: "câble électrique de section..." ❌ (AJOUT)

Réponds UNIQUEMENT avec un JSON :
{{
  "texte_corrige": "texte avec fautes corrigées",
  "corrections": [
    {{"original": "curant", "corrige": "courant", "type": "orthographe"}},
    {{"original": "cable", "corrige": "câble", "type": "accent"}}
  ],
  "nb_corrections": 2,
  "confiance": 0.95
}}

Si aucune faute détectée, retourne le texte original dans "texte_corrige" avec corrections=[] et nb_corrections=0.

JSON uniquement :"""
    
    def corriger(self, texte: str, utiliser_cache: bool = True) -> Dict[str, Any]:
        """
        Corrige l'orthographe d'un texte
        
        Args:
            texte: Texte à corriger
            utiliser_cache: Utiliser le cache pour éviter appels LLM répétés
            
        Returns:
            Dictionnaire avec texte corrigé et détails des corrections
        """
        try:
            # Validation
            if not texte or len(texte.strip()) < 2:
                return self._resultat_vide(texte, "Texte trop court")
            
            texte = texte.strip()
            
            # Vérification cache
            if utiliser_cache and texte in self.cache:
                logger.info("💾 Correction trouvée en cache")
                return self.cache[texte]
            
            # Appel LLM
            logger.info(f"🔍 Correction orthographique : '{texte[:30]}...'")
            prompt = self.prompt_template.format(texte_brut=texte)
            
            response = self.llm.invoke(prompt)
            reponse_llm = response.content if hasattr(response, 'content') else str(response)
            
            # Parsing JSON
            resultat = self._parser_reponse(reponse_llm, texte)
            
            # Mise en cache
            if utiliser_cache:
                self.cache[texte] = resultat
            
            # Logging
            if resultat['nb_corrections'] > 0:
                logger.info(f"✅ {resultat['nb_corrections']} correction(s) appliquée(s)")
            else:
                logger.info("✅ Aucune faute détectée")
            
            return resultat
            
        except Exception as e:
            logger.error(f"❌ Erreur correction : {e}", exc_info=True)
            return self._resultat_erreur(texte, str(e))
    
    def corriger_batch(self, textes: List[str]) -> List[Dict[str, Any]]:
        """
        Corrige plusieurs textes en lot
        
        Args:
            textes: Liste de textes à corriger
            
        Returns:
            Liste des résultats de correction
        """
        logger.info(f"📦 Correction de {len(textes)} textes")
        
        resultats = []
        for i, texte in enumerate(textes, 1):
            logger.info(f"🔄 Texte {i}/{len(textes)}")
            resultat = self.corriger(texte)
            resultat['numero'] = i
            resultats.append(resultat)
        
        nb_corrections_total = sum(r['nb_corrections'] for r in resultats)
        logger.info(f"✅ Lot terminé : {nb_corrections_total} corrections au total")
        
        return resultats
    
    def _parser_reponse(self, reponse_llm: str, texte_original: str) -> Dict[str, Any]:
        """Parse la réponse JSON du LLM"""
        try:
            # Extraction JSON
            json_data = self._extraire_json(reponse_llm)
            
            if json_data:
                return self._valider_resultat(json_data, texte_original)
            else:
                # Fallback : retourner texte original
                logger.warning("⚠️ JSON non détecté, aucune correction appliquée")
                return self._resultat_vide(texte_original, "JSON invalide")
                
        except Exception as e:
            logger.error(f"❌ Erreur parsing : {e}")
            return self._resultat_erreur(texte_original, str(e))
    
    def _extraire_json(self, texte: str) -> Dict[str, Any]:
        """Extrait le JSON de la réponse LLM"""
        try:
            # Chercher JSON avec backticks
            json_match = re.search(r'```json\s*(.*?)\s*```', texte, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Chercher JSON sans backticks
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', texte, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
                
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON invalide : {e}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction : {e}")
        
        return {}
    
    def _valider_resultat(self, json_data: Dict, texte_original: str) -> Dict[str, Any]:
        """Valide et complète le résultat JSON"""
        
        texte_corrige = json_data.get('texte_corrige', texte_original)
        corrections = json_data.get('corrections', [])
        nb_corrections = json_data.get('nb_corrections', len(corrections))
        confiance = json_data.get('confiance', 0.5)
        
        # Validation : si le texte corrigé est trop différent, c'est une reformulation
        if self._est_reformulation(texte_original, texte_corrige):
            logger.warning("⚠️ Reformulation détectée, rejet de la correction")
            return self._resultat_vide(texte_original, "Reformulation détectée")
        
        return {
            "statut": "SUCCESS",
            "texte_original": texte_original,
            "texte_corrige": texte_corrige,
            "corrections": corrections,
            "nb_corrections": nb_corrections,
            "confiance": max(0.0, min(1.0, confiance)),
            "a_ete_corrige": nb_corrections > 0
        }
    
    def _est_reformulation(self, original: str, corrige: str) -> bool:
        """
        Détecte si le texte corrigé est une reformulation abusive
        Critères : longueur trop différente, trop de mots ajoutés
        """
        # Différence de longueur > 50% = probable reformulation
        ratio_longueur = len(corrige) / max(len(original), 1)
        if ratio_longueur > 1.5 or ratio_longueur < 0.7:
            return True
        
        # Nombre de mots ajoutés
        mots_original = set(original.lower().split())
        mots_corrige = set(corrige.lower().split())
        mots_ajoutes = mots_corrige - mots_original
        
        # Si plus de 3 mots ajoutés = reformulation
        if len(mots_ajoutes) > 3:
            return True
        
        return False
    
    def _resultat_vide(self, texte: str, raison: str) -> Dict[str, Any]:
        """Retourne un résultat sans correction"""
        return {
            "statut": "NO_CORRECTION",
            "texte_original": texte,
            "texte_corrige": texte,
            "corrections": [],
            "nb_corrections": 0,
            "confiance": 1.0,
            "a_ete_corrige": False,
            "raison": raison
        }
    
    def _resultat_erreur(self, texte: str, erreur: str) -> Dict[str, Any]:
        """Retourne un résultat d'erreur"""
        return {
            "statut": "ERROR",
            "texte_original": texte,
            "texte_corrige": texte,
            "corrections": [],
            "nb_corrections": 0,
            "confiance": 0.0,
            "a_ete_corrige": False,
            "erreur": erreur
        }
    
    def vider_cache(self):
        """Vide le cache des corrections"""
        nb_entrees = len(self.cache)
        self.cache.clear()
        logger.info(f"🗑️ Cache vidé : {nb_entrees} entrées supprimées")
    
    def statistiques_cache(self) -> Dict[str, Any]:
        """Retourne des statistiques sur le cache"""
        return {
            "nb_entrees": len(self.cache),
            "taille_memoire_approx": sum(len(k) + len(str(v)) for k, v in self.cache.items())
        }


# =============================================================================
# FONCTION UTILITAIRE
# =============================================================================

_orthographe_corrector_instance = None

def get_orthographe_corrector(reset: bool = False) -> OrthographeCorrector:
    """
    Retourne l'instance singleton du correcteur
    
    Args:
        reset: Si True, recrée une nouvelle instance
    """
    global _orthographe_corrector_instance
    if _orthographe_corrector_instance is None or reset:
        _orthographe_corrector_instance = OrthographeCorrector()
    return _orthographe_corrector_instance


def corriger_orthographe_rapide(texte: str) -> str:
    """
    Fonction simple pour correction rapide
    
    Args:
        texte: Texte à corriger
        
    Returns:
        Texte corrigé
    """
    corrector = get_orthographe_corrector()
    resultat = corrector.corriger(texte)
    return resultat['texte_corrige']


# =============================================================================
# TEST ET DÉMONSTRATION
# =============================================================================

if __name__ == "__main__":
    print("✅ TEST ORTHOGRAPHE CORRECTOR")
    print("=" * 70)
    
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    corrector = get_orthographe_corrector()
    
    # Tests
    tests = [
        "le curant nominal",
        "cable abimé dans la cuisne",
        "disjoncteur differanciel manquant",
        "prise pas terre",
        "protection parafoudre non conforme",
        "Le courant",  # Test court
        "cable",       # Test très court
    ]
    
    print(f"\n🔧 Test de {len(tests)} cas...\n")
    
    for i, test in enumerate(tests, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(tests)}: '{test}'")
        print('='*70)
        
        resultat = corrector.corriger(test)
        
        print(f"\n📊 RÉSULTAT :")
        print(f"   Statut : {resultat['statut']}")
        print(f"   Original : {resultat['texte_original']}")
        print(f"   Corrigé : {resultat['texte_corrige']}")
        print(f"   Nombre de corrections : {resultat['nb_corrections']}")
        print(f"   Confiance : {resultat['confiance']:.2f}")
        
        if resultat['corrections']:
            print(f"\n   Détail des corrections :")
            for corr in resultat['corrections']:
                print(f"      • {corr.get('original', '?')} → {corr.get('corrige', '?')} ({corr.get('type', 'inconnu')})")
    
    # Statistiques cache
    print(f"\n{'='*70}")
    print("📊 STATISTIQUES CACHE :")
    stats = corrector.statistiques_cache()
    print(f"   Entrées en cache : {stats['nb_entrees']}")
    print(f"   Taille mémoire approx : {stats['taille_memoire_approx']} octets")
    print('='*70)
    
    print("\n✅ MODULE ORTHOGRAPHE CORRECTOR OPÉRATIONNEL !")
    print("   Prêt pour intégration avant SuggestionEngine")