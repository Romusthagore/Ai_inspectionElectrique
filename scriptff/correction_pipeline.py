#!/usr/bin/env python3
"""
Pipeline de correction automatique d'observations électriques
VERSION CORRIGÉE : Validation de longueur minimale obligatoire
Utilise ContextBuilder + Groq LLM pour générer des corrections structurées
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from groq_config import GroqLLMClient
from context_builder import get_context_builder
from config import CORRECTION_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class CorrectionPipeline:
    """
    Pipeline complet de correction et enrichissement d'observations
    VERSION CORRIGÉE : N'accepte QUE les observations complètes (≥20 caractères, ≥4 mots)
    """
    
    # SEUILS DE VALIDATION
    MIN_LENGTH_CORRECTION = 20     # Minimum 20 caractères
    MIN_WORDS_CORRECTION = 4       # Minimum 4 mots
    
    def __init__(self, context_builder=None, llm_model: str = None, temperature: float = 0.1):
        """
        Args:
            context_builder: Instance du ContextBuilder (optionnel)
            llm_model: Modèle LLM à utiliser (optionnel)
            temperature: Température pour la génération (défaut: 0.1)
        """
        self.llm = GroqLLMClient(model=llm_model, temperature=temperature)
        self.context_builder = context_builder or get_context_builder()
        logger.info(f"✅ CorrectionPipeline initialisé avec modèle: {self.llm.model}")
        logger.info(f"📏 Validation activée : min {self.MIN_LENGTH_CORRECTION} caractères, {self.MIN_WORDS_CORRECTION} mots")
    
    def corriger_observation(self, observation_brute: str, k_documents: int = 5) -> Dict[str, Any]:
        """
        Corrige une observation et retourne un résultat structuré
        VERSION CORRIGÉE : Validation de longueur obligatoire
        
        Args:
            observation_brute: Observation saisie par l'inspecteur
            k_documents: Nombre de documents pour le contexte
            
        Returns:
            Résultat structuré avec observation corrigée et métadonnées
        """
        try:
            observation_brute = observation_brute.strip()
            
            # VALIDATION DE LONGUEUR MINIMALE
            nb_caracteres = len(observation_brute)
            nb_mots = len(observation_brute.split())
            
            if nb_caracteres < self.MIN_LENGTH_CORRECTION or nb_mots < self.MIN_WORDS_CORRECTION:
                logger.warning(f"⚠️ Observation trop courte : {nb_caracteres} car, {nb_mots} mots")
                return self._resultat_observation_incomplete(
                    observation_brute, nb_caracteres, nb_mots
                )
            
            logger.info(f"🔍 Correction: '{observation_brute[:50]}...'")
            
            # 1. Construire le contexte normatif
            contexte_data = self.context_builder.build_context(observation_brute, k=k_documents)
            
            # 2. Préparer le prompt de correction
            prompt = self._preparer_prompt(observation_brute, contexte_data)
            
            # 3. Appel LLM
            try:
                if hasattr(self.llm, 'client') and hasattr(self.llm.client, 'chat'):
                    response = self.llm.client.chat.completions.create(
                        model=self.llm.model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=self.llm.temperature,
                        max_tokens=2000
                    )
                    reponse_llm = response.choices[0].message.content
                else:
                    prompt_complet = f"{SYSTEM_PROMPT}\n\n{prompt}"
                    reponse_llm = self.llm.invoke(prompt_complet)
            except AttributeError:
                prompt_complet = f"{SYSTEM_PROMPT}\n\n{prompt}"
                reponse_llm = self.llm.invoke(prompt_complet)
            
            # 4. Parser la réponse structurée
            resultat_corrige = self._parser_reponse(reponse_llm)
            
            # 5. Enrichir avec métadonnées
            resultat_final = self._enrichir_resultat(
                resultat_corrige, observation_brute, contexte_data
            )
            
            logger.info(f"✅ Observation corrigée: {resultat_final['niveau_gravite']}")
            return resultat_final
            
        except Exception as e:
            logger.error(f"❌ Erreur correction: {e}", exc_info=True)
            return self._resultat_erreur(observation_brute, str(e))
    
    def _resultat_observation_incomplete(
        self, 
        observation: str, 
        nb_caracteres: int, 
        nb_mots: int
    ) -> Dict[str, Any]:
        """
        Retourne un résultat structuré pour observation incomplète
        """
        return {
            "statut": "INCOMPLETE",
            "observation_brute": observation,
            "observation_corrigee": "",
            "references_normatives": [],
            "niveau_gravite": "Indéterminé",
            "risques_identifies": [],
            "actions_correctives": [],
            "delai_recommande": "",
            "localisation": "",
            
            "contexte_utilise": {
                "documents_count": 0,
                "documents_details": [],
                "scores_similarite": []
            },
            
            "erreur": {
                "type": "OBSERVATION_INCOMPLETE",
                "message": f"Observation trop courte pour correction complète",
                "details": {
                    "caracteres_actuels": nb_caracteres,
                    "caracteres_requis": self.MIN_LENGTH_CORRECTION,
                    "mots_actuels": nb_mots,
                    "mots_requis": self.MIN_WORDS_CORRECTION
                },
                "suggestion": "Veuillez compléter l'observation avec plus de détails (minimum 20 caractères et 4 mots)"
            },
            
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.2_VALIDATED"
        }
    
    def _preparer_prompt(self, observation: str, contexte_data: Dict) -> str:
        """Prépare le prompt pour le LLM"""
        context_text = contexte_data.get("context_text", "")
        
        if not context_text:
            context_text = "Aucun contexte normatif trouvé. Utilise tes connaissances sur la NFC 15-100."
        
        prompt = CORRECTION_PROMPT.format(
            observation_brute=observation,
            context=context_text
        )
        
        return prompt
    
    def _parser_reponse(self, reponse_llm: str) -> Dict[str, Any]:
        """Parse la réponse LLM en JSON structuré"""
        reponse_clean = reponse_llm.strip()
        
        # Essayer d'extraire le JSON
        json_data = self._extraire_json(reponse_clean)
        if json_data:
            return self._valider_et_completer_json(json_data)
        
        # Fallback: parsing intelligent
        logger.warning("⚠️ JSON non détecté, utilisation du parser intelligent")
        return self._parser_intelligent(reponse_clean)
    
    def _extraire_json(self, texte: str) -> Optional[Dict[str, Any]]:
        """Extrait et parse le JSON de la réponse"""
        try:
            # Chercher du JSON avec backticks
            json_match = re.search(r'```json\s*(.*?)\s*```', texte, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Chercher du JSON sans backticks
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', texte, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
                
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON invalide: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction JSON: {e}")
        
        return None
    
    def _valider_et_completer_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et complète les champs JSON obligatoires"""
        champs_requis = {
            "observation_corrigee": "Observation non corrigée",
            "references_normatives": [],
            "niveau_gravite": "Mineur",
            "risques_identifies": ["À évaluer"],
            "actions_correctives": ["À définir"],
            "delai_recommande": "30 jours",
            "localisation": "non spécifiée"
        }
        
        for champ, valeur_defaut in champs_requis.items():
            if champ not in json_data or not json_data[champ]:
                json_data[champ] = valeur_defaut
        
        # Normaliser le niveau de gravité
        if json_data["niveau_gravite"] not in ["Critique", "Majeur", "Mineur"]:
            json_data["niveau_gravite"] = "Mineur"
        
        return json_data
    
    def _parser_intelligent(self, texte: str) -> Dict[str, Any]:
        """Parsing intelligent si pas de JSON valide"""
        resultat = {
            "observation_corrigee": "",
            "references_normatives": [],
            "niveau_gravite": "Mineur",
            "risques_identifies": [],
            "actions_correctives": [],
            "delai_recommande": "30 jours",
            "localisation": "non spécifiée"
        }
        
        lines = [l.strip() for l in texte.split('\n') if l.strip()]
        texte_complet = " ".join(lines)
        
        # 1. Observation corrigée
        for line in lines:
            if len(line) > 20 and not line.startswith(('**', '#', '-')):
                resultat["observation_corrigee"] = line
                break
        
        if not resultat["observation_corrigee"]:
            resultat["observation_corrigee"] = texte[:200]
        
        # 2. Niveau de gravité
        texte_lower = texte_complet.lower()
        if any(mot in texte_lower for mot in ['critique', 'danger', 'mortel', 'électrocution']):
            resultat["niveau_gravite"] = "Critique"
        elif any(mot in texte_lower for mot in ['majeur', 'grave', 'important']):
            resultat["niveau_gravite"] = "Majeur"
        
        # 3. Références normatives
        refs = re.findall(r'(NF\s*C\s*\d+[-\d]*|Article\s+\d+[.\d]*)', texte_complet, re.IGNORECASE)
        resultat["references_normatives"] = list(set(refs[:5]))
        
        # 4. Risques
        risques_patterns = [
            r'risque[s]?\s*:\s*([^.\n]+)',
            r'danger[s]?\s*:\s*([^.\n]+)',
            r'peut\s+causer\s+([^.\n]+)'
        ]
        for pattern in risques_patterns:
            matches = re.findall(pattern, texte_complet, re.IGNORECASE)
            resultat["risques_identifies"].extend(matches)
        
        if not resultat["risques_identifies"]:
            resultat["risques_identifies"] = ["Risque technique à évaluer"]
        
        # 5. Actions correctives
        actions_patterns = [
            r'action[s]?\s*:\s*([^.\n]+)',
            r'corriger\s+([^.\n]+)',
            r'installer\s+([^.\n]+)',
            r'remplacer\s+([^.\n]+)'
        ]
        for pattern in actions_patterns:
            matches = re.findall(pattern, texte_complet, re.IGNORECASE)
            resultat["actions_correctives"].extend(matches)
        
        if not resultat["actions_correctives"]:
            resultat["actions_correctives"] = ["Vérification et mise en conformité nécessaire"]
        
        return resultat
    
    def _enrichir_resultat(self, resultat_corrige: Dict, observation_brute: str, 
                          contexte_data: Dict) -> Dict[str, Any]:
        """Enrichit le résultat avec les métadonnées du contexte"""
        return {
            "statut": "SUCCESS",
            
            # Données de correction
            "observation_brute": observation_brute,
            "observation_corrigee": resultat_corrige["observation_corrigee"],
            "references_normatives": resultat_corrige["references_normatives"],
            "niveau_gravite": resultat_corrige["niveau_gravite"],
            "risques_identifies": resultat_corrige["risques_identifies"],
            "actions_correctives": resultat_corrige["actions_correctives"],
            "delai_recommande": resultat_corrige["delai_recommande"],
            "localisation": resultat_corrige["localisation"],
            
            # Métadonnées du contexte
            "contexte_utilise": {
                "documents_count": contexte_data.get("documents_used", 0),
                "documents_details": contexte_data.get("documents_details", []),
                "scores_similarite": [
                    doc.get("score", 0.0) for doc in contexte_data.get("documents_details", [])
                ]
            },
            
            # Métadonnées système
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.2_VALIDATED",
            "llm_model": self.llm.model
        }
    
    def _resultat_erreur(self, observation: str, erreur: str) -> Dict[str, Any]:
        """Retourne un résultat d'erreur structuré"""
        return {
            "statut": "ERROR",
            "observation_brute": observation,
            "observation_corrigee": f"[ERREUR] {observation}",
            "references_normatives": [],
            "niveau_gravite": "Inconnu",
            "risques_identifies": ["Erreur système - analyse impossible"],
            "actions_correctives": ["Contacter l'administrateur système"],
            "delai_recommande": "Immédiat",
            "localisation": "non spécifiée",
            "contexte_utilise": {
                "documents_count": 0, 
                "documents_details": [],
                "scores_similarite": []
            },
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.2_VALIDATED",
            "erreur": erreur
        }
    
    def traiter_lot_observations(self, observations: List[str], 
                                 k_documents: int = 5) -> List[Dict[str, Any]]:
        """Traite plusieurs observations en lot avec reporting"""
        resultats = []
        total = len(observations)
        
        logger.info(f"📦 Démarrage traitement lot: {total} observations")
        
        for i, obs in enumerate(observations, 1):
            logger.info(f"🔄 Traitement observation {i}/{total}")
            
            try:
                resultat = self.corriger_observation(obs, k_documents)
                resultat["numero_observation"] = i
                resultats.append(resultat)
                
            except Exception as e:
                logger.error(f"❌ Erreur observation {i}: {e}")
                erreur = self._resultat_erreur(obs, str(e))
                erreur["numero_observation"] = i
                resultats.append(erreur)
        
        # Statistiques du lot
        nb_succes = sum(1 for r in resultats if r.get("statut") == "SUCCESS")
        nb_incomplete = sum(1 for r in resultats if r.get("statut") == "INCOMPLETE")
        nb_erreurs = sum(1 for r in resultats if r.get("statut") == "ERROR")
        
        logger.info(f"✅ Lot terminé: {nb_succes} succès, {nb_incomplete} incomplètes, {nb_erreurs} erreurs")
        
        return resultats
    
    def exporter_resultats(self, resultats: List[Dict[str, Any]], 
                          fichier_sortie: str = "resultats_corrections.json"):
        """Exporte les résultats dans un fichier JSON"""
        try:
            with open(fichier_sortie, 'w', encoding='utf-8') as f:
                json.dump(resultats, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Résultats exportés: {fichier_sortie}")
        except Exception as e:
            logger.error(f"❌ Erreur export: {e}")


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

_correction_pipeline_instance = None

def get_correction_pipeline(reset: bool = False) -> CorrectionPipeline:
    """Retourne l'instance singleton du pipeline"""
    global _correction_pipeline_instance
    if _correction_pipeline_instance is None or reset:
        _correction_pipeline_instance = CorrectionPipeline()
    return _correction_pipeline_instance

def corriger_observation_rapide(observation: str, k_documents: int = 5) -> Dict[str, Any]:
    """Fonction rapide pour correction simple d'une observation"""
    pipeline = get_correction_pipeline()
    return pipeline.corriger_observation(observation, k_documents)


if __name__ == "__main__":
    print("✅ CORRECTION PIPELINE - VERSION VALIDÉE")
    print("📏 Validation activée : minimum 20 caractères, 4 mots")
    print("🔒 Protégé contre reformulations abusives sur inputs courts")