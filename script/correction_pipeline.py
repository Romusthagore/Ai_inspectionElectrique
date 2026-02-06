#!/usr/bin/env python3
"""
Pipeline de correction automatique d'observations électriques
VERSION ULTRA-CIBLEE : Retourne UNIQUEMENT l'observation reformulée
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from groq_config import GroqLLMClient
from context_builder import get_context_builder

logger = logging.getLogger(__name__)


class CorrectionPipeline:
    """
    Pipeline de correction - VERSION MINIMALISTE
    Retourne UNIQUEMENT le texte corrigé, rien d'autre
    """
    
    # PROMPT TRÈS STRICT : juste la reformulation
    CORRECTION_PROMPT = """Reformule cette observation technique en une seule phrase en français correct.
Concentre-toi uniquement sur la reformulation, ne donne aucun autre texte.

Observation à reformuler : "{observation_brute}"

Réponse : UNIQUEMENT la phrase reformulée. Pas de titre, pas de sections, pas de N/A, rien d'autre.
"""
    
    MIN_LENGTH_CORRECTION = 20
    MIN_WORDS_CORRECTION = 4
    
    def __init__(self, context_builder=None, llm_model: str = None, temperature: float = 0.1):
        self.llm = GroqLLMClient(model=llm_model, temperature=temperature)
        self.context_builder = context_builder or get_context_builder()
        logger.info(f"✅ CorrectionPipeline minimaliste initialisé")
    
    def corriger_observation(self, observation_brute: str, k_documents: int = 3) -> Dict[str, Any]:
        """
        Retourne UNIQUEMENT l'observation reformulée
        """
        try:
            observation_brute = observation_brute.strip()
            
            # Validation de longueur
            nb_caracteres = len(observation_brute)
            nb_mots = len(observation_brute.split())
            
            if nb_caracteres < self.MIN_LENGTH_CORRECTION or nb_mots < self.MIN_WORDS_CORRECTION:
                return {
                    "statut": "INCOMPLETE",
                    "observation_brute": observation_brute,
                    "observation_corrigee": "",
                    "erreur": f"Trop court"
                }
            
            logger.info(f"🔍 Reformulation: '{observation_brute[:50]}...'")
            
            # 1. Prompt ultra-strict
            prompt = self.CORRECTION_PROMPT.format(observation_brute=observation_brute)
            
            # 2. Appel LLM avec instructions très claires
            try:
                system_message = """Tu es un assistant qui reformule des observations techniques.
RÈGLE ABSOLUE : Ne donne QUE la phrase reformulée, sans aucun autre texte.
Pas de titres, pas de sections, pas de N/A, pas d'explications."""
                
                if hasattr(self.llm, 'client') and hasattr(self.llm.client, 'chat'):
                    response = self.llm.client.chat.completions.create(
                        model=self.llm.model,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=100
                    )
                    reponse_llm = response.choices[0].message.content.strip()
                else:
                    reponse_llm = self.llm.invoke(prompt).strip()
            except Exception as e:
                logger.error(f"❌ Erreur LLM: {e}")
                reponse_llm = self._reformulation_minimaliste(observation_brute)
            
            # 3. NETTOYAGE AGGRESSIF - ENLÈVE TOUT SAUF LA PHRASE
            observation_corrigee = self._nettoyer_aggressif(reponse_llm)
            
            # 4. Si après nettoyage c'est vide ou contient N/A, on recommence
            if not observation_corrigee or "N/A" in observation_corrigee:
                logger.warning("⚠️ Réponse vide ou contient N/A, deuxième tentative")
                observation_corrigee = self._reformulation_manuelle(observation_brute)
            
            return {
                "statut": "SUCCESS",
                "observation_brute": observation_brute,
                "observation_corrigee": observation_corrigee,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return {
                "statut": "ERROR",
                "observation_brute": observation_brute,
                "observation_corrigee": observation_brute,
                "erreur": str(e)
            }
    
    def _nettoyer_aggressif(self, texte: str) -> str:
        """
        Nettoyage ULTRA-AGGRESSIF pour garder uniquement la phrase
        """
        if not texte:
            return ""
        
        # 1. Supprimer TOUS les emojis et symboles spéciaux
        texte = re.sub(r'[✨📊⏱️📚•*\-➡️✅⚠️❌🔍🎯📝📄🔧]', '', texte)
        
        # 2. Supprimer les lignes avec "Observation reformulée", "Gravité", "Délai", "Références"
        lignes = texte.split('\n')
        lignes_filtrees = []
        
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne:
                continue
                
            # Supprimer les lignes qui commencent par ces motifs
            motifs_a_supprimer = [
                r'^.*observation.*reformulée.*',
                r'^.*observation.*corrigée.*', 
                r'^.*gravité.*',
                r'^.*délai.*',
                r'^.*recommandé.*',
                r'^.*référence.*',
                r'^.*normative.*',
                r'^N/A.*',
                r'^```.*',
                r'^[-*•]\s+',
                r'^\d+[\.\)]\s+'
            ]
            
            supprimer = False
            for motif in motifs_a_supprimer:
                if re.match(motif, ligne, re.IGNORECASE):
                    supprimer = True
                    break
            
            if not supprimer:
                lignes_filtrees.append(ligne)
        
        texte = ' '.join(lignes_filtrees)
        
        # 3. Supprimer les marqueurs restants
        nettoyages = [
            r'^["\'`]*',  # Guillemets au début
            r'["\'`]*$',  # Guillemets à la fin
            r'^.*:\s*',   # Texte avant deux-points
            r'\s*\(.*\)', # Parenthèses et leur contenu
            r'\s*\[.*\]', # Crochets et leur contenu
        ]
        
        for pattern in nettoyages:
            texte = re.sub(pattern, '', texte)
        
        # 4. Garder seulement la première phrase
        phrases = re.split(r'[.!?]', texte)
        if phrases and phrases[0].strip():
            texte = phrases[0].strip()
        else:
            texte = texte.strip()
        
        # 5. Capitaliser si nécessaire
        if texte and texte[0].islower():
            texte = texte[0].upper() + texte[1:]
        
        # 6. Dernier check : si le texte contient encore "N/A" ou est trop court
        if "N/A" in texte or len(texte) < 10:
            return ""
        
        return texte
    
    def _reformulation_minimaliste(self, observation: str) -> str:
        """
        Reformulation manuelle ultra-minimaliste
        """
        # Mettre la première lettre en majuscule
        if observation and observation[0].islower():
            observation = observation[0].upper() + observation[1:]
        
        # Corrections simples
        corrections = {
            r'\bN/A\b': '',
            r'\bprisen?\b': 'prise de courant',
            r'\bDDR\b': 'disjoncteur différentiel',
            r'\bIP\s*(\d+)\s*[Xx]\b': r'IP\1X',
            r'\s+': ' ',  # Espaces multiples -> simple
        }
        
        for pattern, replacement in corrections.items():
            observation = re.sub(pattern, replacement, observation, flags=re.IGNORECASE)
        
        return observation.strip()
    
    def _reformulation_manuelle(self, observation: str) -> str:
        """
        Reformulation manuelle de secours
        """
        observation_lower = observation.lower()
        
        # Identifier le type d'action
        if any(mot in observation_lower for mot in ['remplacer', 'changer', 'échanger']):
            verbe = "Remplacer"
        elif any(mot in observation_lower for mot in ['installer', 'mettre', 'poser']):
            verbe = "Installer"
        elif any(mot in observation_lower for mot in ['vérifier', 'contrôler', 'tester']):
            verbe = "Vérifier"
        elif any(mot in observation_lower for mot in ['nettoyer', 'dégager', 'nettoyage']):
            verbe = "Nettoyer"
        elif any(mot in observation_lower for mot in ['protéger', 'sécuriser']):
            verbe = "Protéger"
        else:
            verbe = "Corriger"
        
        # Extraire l'objet
        if 'prise' in observation_lower:
            objet = "la prise de courant"
        elif 'disjoncteur' in observation_lower or 'ddr' in observation_lower:
            objet = "le disjoncteur différentiel"
        elif 'câble' in observation_lower or 'cable' in observation_lower:
            objet = "les câbles"
        elif 'luminaire' in observation_lower:
            objet = "le luminaire"
        elif 'tableau' in observation_lower:
            objet = "le tableau électrique"
        elif 'terre' in observation_lower:
            objet = "la liaison à la terre"
        else:
            objet = "l'équipement"
        
        # Construire la phrase
        phrase = f"{verbe} {objet}"
        
        # Ajouter des précisions si disponibles
        if 'sécurité' in observation_lower or 'sécurisé' in observation_lower:
            phrase += " par un modèle de sécurité"
        
        if '30ma' in observation_lower or '30 mA' in observation_lower:
            phrase += " 30mA"
        
        if 'type a' in observation_lower:
            phrase += " de type A"
        
        return phrase
    
    def traiter_lot_observations(self, observations: List[str], 
                                 k_documents: int = 5) -> List[Dict[str, Any]]:
        """Traite plusieurs observations"""
        return [self.corriger_observation(obs, k_documents) for obs in observations]
    
    def exporter_resultats(self, resultats: List[Dict[str, Any]], 
                          fichier_sortie: str = "resultats_corrections.json"):
        """Exporte les résultats"""
        try:
            with open(fichier_sortie, 'w', encoding='utf-8') as f:
                json.dump(resultats, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Export: {fichier_sortie}")
        except Exception as e:
            logger.error(f"❌ Erreur export: {e}")


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

_correction_pipeline_instance = None

def get_correction_pipeline(reset: bool = False) -> CorrectionPipeline:
    global _correction_pipeline_instance
    if _correction_pipeline_instance is None or reset:
        _correction_pipeline_instance = CorrectionPipeline()
    return _correction_pipeline_instance

def corriger_observation_rapide(observation: str, k_documents: int = 5) -> Dict[str, Any]:
    pipeline = get_correction_pipeline()
    return pipeline.corriger_observation(observation, k_documents)

def obtenir_reformulation(observation: str) -> str:
    """
    Fonction PRINCIPALE : retourne UNIQUEMENT le texte reformulé
    Sans N/A, sans sections, sans rien d'autre
    """
    try:
        pipeline = get_correction_pipeline()
        resultat = pipeline.corriger_observation(observation)
        
        if resultat.get("statut") == "SUCCESS":
            texte = resultat.get("observation_corrigee", observation)
            # Dernier nettoyage de sécurité
            texte = re.sub(r'\bN/A\b', '', texte)
            texte = texte.strip()
            return texte if texte else observation
        else:
            return observation
            
    except Exception:
        return observation


if __name__ == "__main__":
    print("✅ CORRECTION PIPELINE - VERSION ULTRA-MINIMALISTE")
    print("🎯 Objectif : UNIQUEMENT la phrase reformulée")
    print("🚫 PAS de N/A, PAS de sections, PAS d'emojis")
    
    # Test spécifique avec votre exemple
    print("\n" + "=" * 70)
    print("🧪 TEST AVEC VOTRE EXEMPLE :")
    print("=" * 70)
    
    exemple_probleme = """✨ **Observation reformulée :**

Remplacez la prise de courant par un modèle de sécurité qui empêche les coupures en charge

📊 **Gravité :** N/A
⏱️ **Délai recommandé :** N/A"""
    
    print(f"\n📝 Input (format problématique):")
    print(f"'{exemple_probleme[:100]}...'")
    
    # Simuler ce que le LLM pourrait retourner
    pipeline = CorrectionPipeline()
    
    # Test 1 : Nettoyage du format problématique
    texte_nettoye = pipeline._nettoyer_aggressif(exemple_probleme)
    print(f"\n✅ Après nettoyage agressif :")
    print(f"'{texte_nettoye}'")
    
    # Test 2 : Avec une vraie observation
    tests = [
        "remplacer la prise par un modèle de sécurité",
        "installer un DDR 30mA type A",
        "vérifier la terre dans la cuisine",
        "nettoyer le tableau électrique",
    ]
    
    print("\n" + "=" * 70)
    print("🧪 TESTS DIVERS :")
    print("=" * 70)
    
    for test in tests:
        reformulee = obtenir_reformulation(test)
        print(f"\n📝 Original: '{test}'")
        print(f"✅ Reformulé: '{reformulee}'")
        
        # Vérifier qu'il n'y a pas de N/A
        if "N/A" in reformulee:
            print(f"❌ PROBLÈME : Contient N/A !")
        if "✨" in reformulee or "📊" in reformulee or "⏱️" in reformulee:
            print(f"❌ PROBLÈME : Contient des emojis !")
        if "Observation reformulée" in reformulee or "Gravité" in reformulee:
            print(f"❌ PROBLÈME : Contient des titres !")
            