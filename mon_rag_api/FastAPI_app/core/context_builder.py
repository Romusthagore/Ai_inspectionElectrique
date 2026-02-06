#!/usr/bin/env python3
"""
ContextBuilder SIMPLE et FONCTIONNEL
Version définitive pour le pipeline de correction
"""

import logging
from typing import List, Dict, Any
from core.retriever import get_retriever

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    ContextBuilder simple et efficace
    Interface propre pour le CorrectionPipeline
    """
    
    def __init__(self, retriever=None):
        """
        Args:
            retriever: Instance du retriever (optionnel)
        """
        self.retriever = retriever or get_retriever()
        logger.info("✅ ContextBuilder initialisé")
    
    def build_context(self, observation: str, k: int = 5) -> Dict[str, Any]:
        """
        Construit le contexte pour une observation
        
        Args:
            observation: Observation à corriger
            k: Nombre de documents à récupérer
            
        Returns:
            Contexte structuré
        """
        try:
            logger.info(f"🔄 Construction contexte: '{observation}' (k={k})")
            
            # 1. Récupérer les documents pertinents
            documents = self.retriever.get_relevant_documents(observation, k=k)
            
            # 2. Construire le contexte textuel
            context_text = self._build_context_text(documents, observation)
            
            # 3. Structurer la réponse
            result = {
                "observation": observation,
                "context_text": context_text,
                "documents_used": len(documents),
                "documents_details": [
                    {
                        'norme': doc.get('norme', 'N/A'),
                        'article': doc.get('article', 'N/A'),
                        'type': doc.get('type_document', 'N/A'),
                        'score': doc.get('similarity_score', 0.0)
                    }
                    for doc in documents
                ]
            }
            
            logger.info(f"✅ Contexte construit: {len(documents)} documents")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur construction contexte: {e}")
            return self._build_error_context(observation, str(e))
    
    def _build_context_text(self, documents: List[Dict], observation: str) -> str:
        """
        Construit le texte de contexte UNIQUEMENT avec références
        VERSION CORRIGÉE : Ne donne PAS le contenu complet
        """
        if not documents:
            return f"Aucun document pertinent trouvé pour: {observation}"
        
        context_parts = []
        
        # En-tête
        context_parts.append(f"# CONTEXTE NORMATIF (RÉFÉRENCES UNIQUEMENT)")
        context_parts.append(f"Observation brute : {observation}")
        context_parts.append(f"Documents pertinents trouvés : {len(documents)}")
        context_parts.append("")
        
        # NOUVEAU : Liste compacte des références
        context_parts.append("## RÉFÉRENCES NORMATIVES APPLICABLES")
        context_parts.append("")
        
        for i, doc in enumerate(documents, 1):
            # Extraire seulement les métadonnées importantes
            norme = doc.get('norme', 'N/A')
            article = doc.get('article', 'N/A')
            score = doc.get('similarity_score', 0)
            
            # Format compact : juste la référence
            context_parts.append(
                f"{i}. {norme} {article} (pertinence: {score:.2f})"
            )
            
            # OPTIONNEL : Titre/résumé court (max 50 caractères)
            # Ne pas inclure le contenu complet
            content_preview = doc.get('content', '')[:50].strip()
            if content_preview:
                context_parts.append(f"   → {content_preview}...")
            
            context_parts.append("")
        
        # Instructions STRICTES
        context_parts.append("")
        context_parts.append("## ⚠️ INSTRUCTIONS IMPÉRATIVES")
        context_parts.append("")
        context_parts.append("Les références ci-dessus sont fournies UNIQUEMENT pour citation.")
        context_parts.append("")
        context_parts.append("VOUS DEVEZ :")
        context_parts.append("✅ Reformuler l'observation en terminologie technique")
        context_parts.append("✅ Citer les références normatives listées ci-dessus")
        context_parts.append("✅ Rester strictement FACTUEL")
        context_parts.append("")
        context_parts.append("VOUS NE DEVEZ PAS :")
        context_parts.append("❌ Ajouter des informations non présentes dans l'observation brute")
        context_parts.append("❌ Inventer des causes ou hypothèses")
        context_parts.append("❌ Utiliser le contenu des articles pour enrichir l'observation")
        context_parts.append("❌ Écrire 'potentiellement dû à', 'en violation de', etc.")
        context_parts.append("")
        context_parts.append("EXEMPLE :")
        context_parts.append("• Observation: 'feu dans salle de bain'")
        context_parts.append("• ✅ BON: 'Incendie constaté dans la salle de bain'")
        context_parts.append("• ❌ MAUVAIS: 'Incendie dû à un défaut de protection...'")
        
        return "\n".join(context_parts)
    
    def _build_error_context(self, observation: str, error: str) -> Dict[str, Any]:
        """Construit un contexte d'erreur"""
        return {
            "observation": observation,
            "context_text": f"ERREUR: {error}\n\nObservation: {observation}",
            "documents_used": 0,
            "documents_details": [],
            "error": error
        }


# =============================================================================
# SINGLETON ET FONCTIONS UTILITAIRES
# =============================================================================

_context_builder_instance = None

def get_context_builder() -> ContextBuilder:
    """Retourne l'instance singleton du ContextBuilder"""
    global _context_builder_instance
    if _context_builder_instance is None:
        _context_builder_instance = ContextBuilder()
    return _context_builder_instance

def build_rag_context(observation: str, k: int = 5) -> Dict[str, Any]:
    """Fonction utilitaire pour construction rapide de contexte"""
    return get_context_builder().build_context(observation, k)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("🧪 TEST CONTEXT BUILDER SIMPLE")
    print("=" * 50)
    
    builder = get_context_builder()
    
    # Test avec paramètre k
    print("🔧 Test avec k=2...")
    context = builder.build_context("protection différentielle", k=2)
    
    print(f"✅ {context['documents_used']} documents trouvés")
    print(f"📊 Détails: {context['documents_details']}")
    print(f"📝 Contexte (début): {context['context_text'][:200]}...")
    
    print("\n🎯 CONTEXT BUILDER SIMPLE FONCTIONNEL !")