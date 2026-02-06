#!/usr/bin/env python3
"""
Pipeline de correction - VERSION SANS LLM
"""
import json
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CorrectionPipeline:
    def __init__(self, context_builder=None, llm_model: str = None, temperature: float = 0.1):
        from core.groq_config import GroqLLMClient
        self.llm = GroqLLMClient(model=llm_model, temperature=temperature)
        logger.info("CorrectionPipeline initialise")

    def corriger_observation(self, observation_brute: str, k_documents: int = 3) -> Dict[str, Any]:
        """Version SANS appel LLM - juste nettoyage basique"""
        try:
            logger.info(f"Reformulation: '{observation_brute[:50]}...'")
            
            # SKIP LE LLM - Juste nettoyer l'observation
            observation_corrigee = observation_brute.strip()
            
            # Capitaliser la première lettre
            if observation_corrigee and observation_corrigee[0].islower():
                observation_corrigee = observation_corrigee[0].upper() + observation_corrigee[1:]
            
            # Corrections basiques
            observation_corrigee = re.sub(r'\s+', ' ', observation_corrigee)  # Espaces multiples
            observation_corrigee = re.sub(r'\bprisen?\b', 'prise de courant', observation_corrigee, flags=re.IGNORECASE)
            observation_corrigee = re.sub(r'\bDDR\b', 'disjoncteur différentiel', observation_corrigee)
            
            logger.info(f"Observation nettoyee: '{observation_corrigee[:50]}...'")
            
            return {
                "statut": "SUCCESS",
                "observation_corrigee": observation_corrigee,
                "source": "correction_pipeline_manual"
            }
            
        except Exception as e:
            logger.error(f"Erreur: {e}")
            return {
                "statut": "ERROR",
                "erreur": "Erreur interne",
                "observation_corrigee": observation_brute
            }


_pipeline_instance = None

def get_correction_pipeline(llm_model: str = None, temperature: float = 0.1):
    """Retourne l'instance singleton du pipeline"""
    global _pipeline_instance
    if _pipeline_instance is None:
        logger.info("Creation de l'instance CorrectionPipeline")
        _pipeline_instance = CorrectionPipeline(
            llm_model=llm_model,
            temperature=temperature
        )
    return _pipeline_instance