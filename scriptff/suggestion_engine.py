#!/usr/bin/env python3
"""
Module SuggestionEngine - Version COMPLÈTE avec toutes les fonctionnalités
Intègre : priorité, actions correctives, validation, structuration rapport
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import re

# Imports LangChain
try:
    from langchain_groq import ChatGroq
    from langchain_core.prompts import PromptTemplate
except ImportError as e:
    print(f"❌ Erreur d'import LangChain : {e}")
    raise

# Import du VectorStore personnalisé
try:
    from vector_store import VectorStore
except ImportError as e:
    print(f"❌ Erreur d'import VectorStore : {e}")
    raise

# Import de la configuration
try:
    from config import (
        CORRECTION_PROMPT,
        CATEGORIES_OBSERVATIONS,
        detecter_categorie,
        get_config_categorie,
        TEMPLATE_OBSERVATION_STANDARD
    )
except ImportError as e:
    print(f"❌ Erreur d'import config : {e}")
    raise

logger = logging.getLogger(__name__)


@dataclass
class SuggestionResult:
    """Structure COMPLÈTE des résultats de suggestions"""
    # Suggestions de base
    mots_cles: List[str]
    phrases_completes: List[str]
    references_normatives: List[str]
    complements_intelligents: List[str]
    
    # NOUVEAU : Évaluation et structuration
    categorie_detectee: str
    niveau_priorite: int  # 1=À surveiller, 2=Planifier, 3=Critique
    niveau_gravite: str  # Critique|Majeur|Mineur
    risques_identifies: List[str]
    actions_correctives: List[str]
    delai_recommande: str
    localisation_suggeree: str
    
    # Métadonnées
    confiance_score: float
    observation_corrigee: str  # Version reformulée complète
    rapport_formate: str  # Format final pour insertion dans rapport
    
    # Alertes qualité
    alertes_coherence: List[str]
    suggestions_amelioration: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SuggestionEngine:
    """
    Moteur de suggestions COMPLET avec correction, évaluation et structuration
    """
    
    def __init__(
        self,
        vectorstore: VectorStore,
        llm: ChatGroq,
        k_documents: int = 5,
        min_similarity: float = 0.3
    ):
        """Initialise le moteur complet"""
        self.vectorstore = vectorstore
        self.llm = llm
        self.k_documents = k_documents
        self.min_similarity = min_similarity
        
        # Templates pour suggestions ET correction
        self.suggestion_template = PromptTemplate(
            input_variables=["user_input", "context_documents"],
            template=self._get_suggestion_prompt_template()
        )
        
        self.correction_template = PromptTemplate(
            input_variables=["observation_brute", "context"],
            template=CORRECTION_PROMPT  # Depuis config.py
        )
        
        # Patterns de détection de risques critiques
        self.patterns_critiques = [
            r'\b(contact direct|électrocution|court.circuit|incendie)\b',
            r'\b(absence.*différentiel|pas.*protection|sans.*terre)\b',
            r'\b(danger.*mort|risque.*grave|immédiat)\b'
        ]
        
        logger.info("✅ SuggestionEngine COMPLET initialisé")
    
    def _get_suggestion_prompt_template(self) -> str:
        """Template optimisé pour suggestions rapides"""
        return """Tu es un assistant spécialisé en normes électriques NFC 15-100.

L'utilisateur tape : "{user_input}"

Contexte normatif disponible :
{context_documents}

GÉNÈRE des suggestions RAPIDES et PERTINENTES en JSON :
{{
  "mots_cles": ["terme1", "terme2", "terme3"],
  "phrases_completes": ["phrase 1", "phrase 2"],
  "references_normatives": ["NFC 15-100 Article X.X"],
  "complements_intelligents": ["complément 1", "complément 2"]
}}

Règles :
- Seulement des suggestions directement liées
- Références RÉELLES du contexte uniquement
- Maximum 6 mots-clés, 4 phrases, 5 références

JSON uniquement :"""
    
    def get_suggestions(
        self, 
        user_input: str,
        localisation: Optional[str] = None,
        mode: str = "rapide"
    ) -> SuggestionResult:
        """
        Génère suggestions COMPLÈTES avec correction et évaluation
        
        Args:
            user_input: Texte saisi par l'utilisateur
            localisation: Zone d'inspection (TGBT, LOCAL GROUPE, etc.)
            mode: "rapide" (suggestions) ou "complet" (correction totale)
            
        Returns:
            SuggestionResult avec toutes les fonctionnalités
        """
        try:
            # Validation
            if not user_input or len(user_input.strip()) < 3:
                return self._get_empty_suggestions("Input trop court")
            
            user_input = user_input.strip()
            
            # 1. Recherche dans VectorStore
            logger.info(f"🔍 Recherche pour : '{user_input}'")
            documents = self._retrieve_relevant_documents(user_input)
            
            if not documents:
                logger.warning("⚠️ Aucun document pertinent")
                return self._get_fallback_suggestions(user_input, localisation)
            
            # 2. Préparation du contexte
            context = self._format_context_documents(documents)
            
            # 3. Mode RAPIDE : suggestions simples
            if mode == "rapide":
                return self._generate_quick_suggestions(user_input, context, localisation)
            
            # 4. Mode COMPLET : correction + évaluation + structuration
            else:
                return self._generate_complete_correction(user_input, context, localisation)
                
        except Exception as e:
            logger.error(f"❌ Erreur get_suggestions : {e}", exc_info=True)
            return self._get_fallback_suggestions(user_input, localisation)
    
    def _generate_quick_suggestions(
        self,
        user_input: str,
        context: str,
        localisation: Optional[str]
    ) -> SuggestionResult:
        """Mode RAPIDE : suggestions légères pour auto-complétion"""
        
        # Génération via LLM
        prompt = self.suggestion_template.format(
            user_input=user_input,
            context_documents=context
        )
        response = self.llm.invoke(prompt)
        suggestions_json = response.content if hasattr(response, 'content') else str(response)
        
        # Parsing
        data = self._parse_json_response(suggestions_json)
        
        # Détection catégorie et gravité préliminaire
        categorie = detecter_categorie(user_input)
        config_cat = get_config_categorie(categorie)
        priorite_prelim = self._evaluer_priorite_preliminaire(user_input, categorie)
        
        # Construction du résultat RAPIDE
        return SuggestionResult(
            mots_cles=self._validate_list(data.get('mots_cles', []), 6),
            phrases_completes=self._validate_list(data.get('phrases_completes', []), 4),
            references_normatives=self._validate_list(
                data.get('references_normatives', []) + config_cat.get('normes', []), 
                5
            ),
            complements_intelligents=self._validate_list(data.get('complements_intelligents', []), 4),
            
            categorie_detectee=categorie,
            niveau_priorite=priorite_prelim,
            niveau_gravite=config_cat.get('gravité_par_défaut', 'Mineur'),
            risques_identifies=self._detecter_risques_rapides(user_input),
            actions_correctives=[],  # Pas générées en mode rapide
            delai_recommande=self._mapper_delai(priorite_prelim),
            localisation_suggeree=localisation or "À préciser",
            
            confiance_score=0.7,
            observation_corrigee="",  # Pas de reformulation en mode rapide
            rapport_formate="",
            
            alertes_coherence=[],
            suggestions_amelioration=self._suggerer_ameliorations_contextuelles(localisation)
        )
    
    def _generate_complete_correction(
        self,
        user_input: str,
        context: str,
        localisation: Optional[str]
    ) -> SuggestionResult:
        """Mode COMPLET : correction structurée avec évaluation"""
        
        # Génération CORRECTION complète via prompt config.py
        prompt = self.correction_template.format(
            observation_brute=user_input,
            context=context
        )
        response = self.llm.invoke(prompt)
        correction_json = response.content if hasattr(response, 'content') else str(response)
        
        # Parsing correction
        data = self._parse_json_response(correction_json)
        
        # Extraction données
        observation_corrigee = data.get('observation_corrigee', user_input)
        references = self._validate_list(data.get('references_normatives', []), 10)
        niveau_gravite = data.get('niveau_gravite', 'Mineur')
        risques = self._validate_list(data.get('risques_identifies', []), 10)
        actions = self._validate_list(data.get('actions_correctives', []), 10)
        delai = data.get('delai_recommande', '90 jours')
        localisation_llm = data.get('localisation', localisation or 'À préciser')
        
        # Mapping gravité -> priorité
        priorite = self._mapper_gravite_to_priorite(niveau_gravite)
        
        # Détection catégorie
        categorie = detecter_categorie(observation_corrigee)
        
        # Validation cohérence
        alertes = self._valider_coherence(
            observation_corrigee, references, niveau_gravite, actions, localisation_llm
        )
        
        # Formatage rapport
        rapport = self._formater_pour_rapport(
            observation_corrigee, localisation_llm, references, 
            niveau_gravite, priorite, actions
        )
        
        # Suggestions d'amélioration contextuelles
        suggestions_amelioration = self._suggerer_ameliorations_contextuelles(localisation_llm)
        
        # Suggestions légères en bonus
        suggestions_quick = self._generate_quick_suggestions(user_input, context, localisation)
        
        # Construction résultat COMPLET
        return SuggestionResult(
            # Suggestions de base
            mots_cles=suggestions_quick.mots_cles,
            phrases_completes=suggestions_quick.phrases_completes,
            references_normatives=references,
            complements_intelligents=suggestions_quick.complements_intelligents,
            
            # Évaluation complète
            categorie_detectee=categorie,
            niveau_priorite=priorite,
            niveau_gravite=niveau_gravite,
            risques_identifies=risques,
            actions_correctives=actions,
            delai_recommande=delai,
            localisation_suggeree=localisation_llm,
            
            # Résultats
            confiance_score=0.9,
            observation_corrigee=observation_corrigee,
            rapport_formate=rapport,
            
            # Qualité
            alertes_coherence=alertes,
            suggestions_amelioration=suggestions_amelioration
        )
    
    def _retrieve_relevant_documents(self, query: str) -> List[Dict[str, Any]]:
        """Récupère documents pertinents via VectorStore"""
        try:
            results = self.vectorstore.search(
                query=query,
                k=self.k_documents,
                score_threshold=self.min_similarity
            )
            logger.info(f"📚 {len(results)} documents trouvés")
            return results
        except Exception as e:
            logger.error(f"Erreur VectorStore : {e}")
            return []
    
    def _format_context_documents(self, documents: List[Dict[str, Any]]) -> str:
        """Formate documents pour contexte LLM"""
        if not documents:
            return "Aucun document pertinent."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.get('content', '')[:500]
            similarity = doc.get('similarity_score', 0)
            norme = doc.get('norme', 'N/A')
            article = doc.get('article', 'N/A')
            
            context_parts.append(
                f"--- Document {i} (pertinence: {similarity:.2f}) ---\n"
                f"Norme: {norme} - Article: {article}\n"
                f"{content}\n"
            )
        
        return "\n".join(context_parts)
    
    def _parse_json_response(self, json_response: str) -> dict:
        """Parse réponse JSON du LLM avec nettoyage"""
        try:
            json_str = json_response.strip()
            
            # Extraction JSON depuis markdown
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON : {e}")
            return {}
    
    def _evaluer_priorite_preliminaire(self, texte: str, categorie: str) -> int:
        """Évalue rapidement la priorité (1/2/3)"""
        texte_lower = texte.lower()
        
        # Priorité 3 (CRITIQUE)
        for pattern in self.patterns_critiques:
            if re.search(pattern, texte_lower, re.IGNORECASE):
                return 3
        
        # Priorité basée sur catégorie
        if categorie in ['mise_à_la_terre', 'protection_foudre']:
            return 3
        elif categorie == 'protection_différentielle':
            return 2
        
        # Mots-clés de gravité
        if any(word in texte_lower for word in ['absence', 'manque', 'défaillant', 'dangereux']):
            return 2
        
        return 1
    
    def _detecter_risques_rapides(self, texte: str) -> List[str]:
        """Détection rapide des risques évidents"""
        risques = []
        texte_lower = texte.lower()
        
        if 'contact direct' in texte_lower or 'nu' in texte_lower:
            risques.append("Risque de contact direct avec pièces sous tension")
        
        if 'différentiel' in texte_lower or 'ddr' in texte_lower:
            risques.append("Risque d'électrocution sans protection différentielle")
        
        if 'terre' in texte_lower:
            risques.append("Risque de choc électrique par défaut de mise à la terre")
        
        if 'câble' in texte_lower or 'section' in texte_lower:
            risques.append("Risque d'échauffement et d'incendie")
        
        return risques if risques else ["Risque à évaluer selon contexte"]
    
    def _mapper_gravite_to_priorite(self, gravite: str) -> int:
        """Convertit gravité textuelle en priorité numérique"""
        mapping = {
            'Critique': 3,
            'critique': 3,
            'CRITIQUE': 3,
            'Majeur': 2,
            'majeur': 2,
            'MAJEUR': 2,
            'Mineur': 1,
            'mineur': 1,
            'MINEUR': 1
        }
        return mapping.get(gravite, 1)
    
    def _mapper_delai(self, priorite: int) -> str:
        """Map priorité -> délai"""
        mapping = {3: 'immédiat', 2: '30 jours', 1: '90 jours'}
        return mapping.get(priorite, '90 jours')
    
    def _valider_coherence(
        self,
        observation: str,
        references: List[str],
        gravite: str,
        actions: List[str],
        localisation: str
    ) -> List[str]:
        """Détecte incohérences et problèmes de qualité"""
        alertes = []
        
        # Vérification références
        if not references or len(references) < 1:
            alertes.append("⚠️ Aucune référence normative trouvée")
        
        # Vérification actions si critique
        if gravite in ['Critique', 'critique', 'CRITIQUE'] and len(actions) < 2:
            alertes.append("⚠️ Gravité critique mais peu d'actions correctives proposées")
        
        # Vérification localisation
        if localisation == "À préciser" or not localisation:
            alertes.append("⚠️ Localisation manquante ou imprécise")
        
        # Vérification longueur observation
        if len(observation) < 30:
            alertes.append("⚠️ Observation trop courte, manque de détails techniques")
        
        return alertes
    
    def _formater_pour_rapport(
        self,
        observation: str,
        localisation: str,
        references: List[str],
        gravite: str,
        priorite: int,
        actions: List[str]
    ) -> str:
        """Formate observation selon template rapport"""
        
        # Utilisation du template depuis config
        rapport = TEMPLATE_OBSERVATION_STANDARD.format(
            observation=observation,
            localisation=localisation,
            reference=" | ".join(references[:3]),  # Max 3 références
            gravite=f"{gravite} (Priorité {priorite})",
            action=" ; ".join(actions[:3])  # Max 3 actions
        )
        
        return rapport
    
    def _suggerer_ameliorations_contextuelles(self, localisation: Optional[str]) -> List[str]:
        """Suggestions d'amélioration selon la zone inspectée"""
        suggestions = []
        
        if not localisation:
            return ["Préciser la localisation pour suggestions contextuelles"]
        
        loc_lower = localisation.lower()
        
        # Suggestions par type de local
        if 'tgbt' in loc_lower or 'armoire' in loc_lower:
            suggestions.extend([
                "Vérifier présence schéma électrique affiché",
                "Contrôler identification des circuits",
                "Vérifier parafoudre en tête de tableau"
            ])
        
        elif 'groupe' in loc_lower or 'génératrice' in loc_lower:
            suggestions.extend([
                "Vérifier ventilation du local",
                "Contrôler arrêt d'urgence fonctionnel",
                "Vérifier démarrage automatique"
            ])
        
        elif 'transformateur' in loc_lower:
            suggestions.extend([
                "Vérifier mise à la terre du neutre",
                "Contrôler bac de rétention (si huile)",
                "Vérifier protection MT/BT"
            ])
        
        else:
            suggestions.append("Compléter avec détails techniques spécifiques à la zone")
        
        return suggestions
    
    def _validate_list(self, items: List[str], max_items: int) -> List[str]:
        """Valide et nettoie une liste"""
        if not isinstance(items, list):
            return []
        
        cleaned = []
        seen = set()
        
        for item in items:
            if isinstance(item, str):
                item = item.strip()
                if item and item not in seen and len(item) > 2:
                    cleaned.append(item)
                    seen.add(item)
                    if len(cleaned) >= max_items:
                        break
        
        return cleaned
    
    def _get_empty_suggestions(self, raison: str) -> SuggestionResult:
        """Retourne suggestions vides"""
        logger.info(f"ℹ️ Suggestions vides : {raison}")
        return SuggestionResult(
            mots_cles=[], phrases_completes=[], references_normatives=[],
            complements_intelligents=[], categorie_detectee='général',
            niveau_priorite=1, niveau_gravite='Mineur', risques_identifies=[],
            actions_correctives=[], delai_recommande='90 jours',
            localisation_suggeree='À préciser', confiance_score=0.0,
            observation_corrigee='', rapport_formate='',
            alertes_coherence=[], suggestions_amelioration=[]
        )
    
    def _get_fallback_suggestions(
        self, 
        user_input: str,
        localisation: Optional[str]
    ) -> SuggestionResult:
        """Suggestions de secours basiques"""
        logger.info("🔄 Utilisation fallback")
        
        user_lower = user_input.lower()
        categorie = detecter_categorie(user_input)
        config_cat = get_config_categorie(categorie)
        
        # Suggestions basiques selon catégorie
        if categorie == 'protection_différentielle':
            mots_cles = ['30mA', 'Type A', 'DDR', 'protection']
            phrases = ['Dispositif différentiel 30mA requis']
            refs = ['NFC 15-100 Article 411.3.3']
            actions = ['Installer DDR 30mA type A', 'Tester le déclenchement']
            risques = ['Électrocution sans protection différentielle']
            priorite = 2
        
        elif categorie == 'mise_à_la_terre':
            mots_cles = ['liaison', 'résistance', 'continuité', 'piquet']
            phrases = ['Mise à la terre défaillante']
            refs = ['NFC 15-100 Article 542']
            actions = ['Vérifier continuité PE', 'Mesurer résistance de terre']
            risques = ['Choc électrique par défaut de mise à la terre']
            priorite = 3
        
        else:
            mots_cles = ['protection', 'conformité', 'vérification']
            phrases = ['Non-conformité détectée']
            refs = ['NFC 15-100']
            actions = ['Corriger selon norme']
            risques = ['À évaluer']
            priorite = 1
        
        gravite = config_cat.get('gravité_par_défaut', 'Mineur')
        
        return SuggestionResult(
            mots_cles=mots_cles,
            phrases_completes=phrases,
            references_normatives=refs,
            complements_intelligents=['Consulter la norme complète'],
            categorie_detectee=categorie,
            niveau_priorite=priorite,
            niveau_gravite=gravite,
            risques_identifies=risques,
            actions_correctives=actions,
            delai_recommande=self._mapper_delai(priorite),
            localisation_suggeree=localisation or 'À préciser',
            confiance_score=0.3,
            observation_corrigee=user_input,
            rapport_formate=self._formater_pour_rapport(
                user_input, localisation or 'À préciser', 
                refs, gravite, priorite, actions
            ),
            alertes_coherence=['Suggestions basiques - contexte insuffisant'],
            suggestions_amelioration=self._suggerer_ameliorations_contextuelles(localisation)
        )


def get_suggestion_engine(vectorstore: VectorStore, llm: ChatGroq) -> SuggestionEngine:
    """Factory function pour créer le SuggestionEngine complet"""
    return SuggestionEngine(
        vectorstore=vectorstore,
        llm=llm,
        k_documents=5,
        min_similarity=0.3
    )


if __name__ == "__main__":
    print("✅ Module SuggestionEngine COMPLET chargé")
    print("📋 Fonctionnalités : suggestions, correction, évaluation, structuration, validation")