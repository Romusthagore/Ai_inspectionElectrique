#!/usr/bin/env python3
"""
Routes API pour le système RAG - Normes Électriques NFC 15-100
Interface REST inspirée de l'architecture PyQt6
Version complète avec CorrectionPipeline et filtrage par thème
"""
import traceback
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["rag"])

# ============================================================================
# MODÈLES PYDANTIC - SCHÉMAS DE DONNÉES
# ============================================================================

class AutocompleteRequest(BaseModel):
    """Requête pour l'autocomplétion avec filtre thème"""
    query: str = Field(..., description="Texte à compléter", min_length=1)
    theme_filter: Optional[str] = Field(None, description="Filtre par thème")
    max_results: int = Field(10, ge=1, le=50, description="Nombre max de résultats")


class AutocompleteResponse(BaseModel):
    """Réponse d'autocomplétion"""
    query: str
    suggestions: List[str]
    count: int
    theme_filter: Optional[str] = None
    matching_themes: Optional[List[str]] = None


class ReformulateRequest(BaseModel):
    """Requête pour la reformulation d'observation"""
    text: str = Field(..., description="Observation à reformuler", min_length=3)
    location: Optional[str] = Field(None, description="Localisation optionnelle")
    theme_filter: Optional[str] = Field(None, description="Filtre par thème")


class ReformulateResponse(BaseModel):
    """Réponse de reformulation complète"""
    observation_corrigee: str
    niveau_gravite: str
    delai_recommande: str
    references_normatives: List[str]
    norme_applicable: Optional[str] = None
    source: str = "correction_pipeline_llm"
    theme_filter_applied: Optional[str] = None


class NormeRequest(BaseModel):
    """Requête pour l'extraction de norme"""
    observation: str = Field(..., description="Observation électrique")
    theme_filter: Optional[str] = Field(None, description="Filtre par thème")


class NormeResponse(BaseModel):
    """Réponse d'extraction de norme"""
    norme: str
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    theme_filter: Optional[str] = None


class SearchResult(BaseModel):
    """Un résultat de recherche"""
    content: str
    metadata: Dict[str, Any]
    score: float
    source: Optional[str] = None
    theme: Optional[str] = None


class SearchRequest(BaseModel):
    """Requête pour la recherche sémantique"""
    query: str = Field(..., description="Question ou recherche")
    theme_filter: Optional[str] = Field(None, description="Filtre par thème")
    max_results: int = Field(5, ge=1, le=20, description="Nombre de résultats")


class SearchResponse(BaseModel):
    """Réponse de recherche"""
    query: str
    results: List[SearchResult]
    count: int
    theme_filter: Optional[str] = None
    matching_themes: Optional[List[str]] = None


class ThemeSearchRequest(BaseModel):
    """Requête de recherche de thèmes"""
    query: str = Field(..., description="Expression de thème (ex: 'éclai', 'protect')")
    min_similarity: Optional[float] = Field(0.5, ge=0.0, le=1.0)


class ThemeSuggestRequest(BaseModel):
    """Requête de suggestions de thèmes"""
    partial_query: str = Field(..., min_length=1, description="Début de thème")
    max_suggestions: Optional[int] = Field(5, ge=1, le=20)


# ============================================================================
# GESTION DES SERVICES - SINGLETON PATTERN
# ============================================================================

# Variables globales pour les services
_suggestion_engine_instance = None
_vector_store_instance = None
_correction_pipeline_instance = None
_prescriptions_instance = None
_theme_searcher_instance = None


def set_suggestion_engine(engine):
    """Définir le moteur de suggestions"""
    global _suggestion_engine_instance
    _suggestion_engine_instance = engine
    logger.info("✅ SuggestionEngine défini")


def set_vector_store(store):
    """Définir le vector store"""
    global _vector_store_instance
    _vector_store_instance = store
    logger.info("✅ VectorStore défini")


def set_correction_pipeline(pipeline):
    """Définir le pipeline de correction"""
    global _correction_pipeline_instance
    _correction_pipeline_instance = pipeline
    logger.info("✅ CorrectionPipeline défini")


def set_prescriptions(prescriptions):
    """Définir les prescriptions"""
    global _prescriptions_instance
    _prescriptions_instance = prescriptions
    logger.info(f"✅ Prescriptions définies: {len(prescriptions)} éléments")


def set_theme_searcher(searcher):
    """Définir le moteur de recherche de thèmes"""
    global _theme_searcher_instance
    _theme_searcher_instance = searcher
    if searcher:
        themes_count = len(searcher.get_available_themes())
        logger.info(f"✅ ThemeSearcher défini: {themes_count} thèmes")
    else:
        logger.info("⚠️ ThemeSearcher non défini")


def get_suggestion_engine():
    """Récupérer le moteur de suggestions"""
    if _suggestion_engine_instance is None:
        raise HTTPException(status_code=503, detail="SuggestionEngine non initialisé")
    return _suggestion_engine_instance


def get_vector_store():
    """Récupérer le vector store"""
    if _vector_store_instance is None:
        raise HTTPException(status_code=503, detail="VectorStore non initialisé")
    return _vector_store_instance


def get_correction_pipeline():
    """Récupérer le pipeline de correction"""
    if _correction_pipeline_instance is None:
        raise HTTPException(status_code=503, detail="CorrectionPipeline non initialisé")
    return _correction_pipeline_instance


def get_prescriptions():
    """Récupérer les prescriptions"""
    if _prescriptions_instance is None:
        raise HTTPException(status_code=503, detail="Prescriptions non chargées")
    return _prescriptions_instance


def get_theme_searcher():
    """Récupérer le moteur de recherche de thèmes"""
    if _theme_searcher_instance is None:
        raise HTTPException(status_code=503, detail="ThemeSearcher non initialisé")
    return _theme_searcher_instance


# ============================================================================
# ENDPOINTS PRINCIPAUX
# ============================================================================

@router.post("/reformulate", response_model=ReformulateResponse)
async def reformulate_observation(request: ReformulateRequest):
    """
    Reformuler une observation - IDENTIQUE à la logique PyQt
    """
    logger.info(f"✨ Reformulation: '{request.text[:50]}...' (theme: {request.theme_filter})")
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Texte vide")
    
    text = request.text.strip()
    location = request.location.strip() if request.location else ""
    theme_filter = request.theme_filter.strip() if request.theme_filter else ""
    
    observation_corrigee = text
    source = "fallback"
    
    # ============================================
    # 1. REFORMULATION AVEC CORRECTION PIPELINE
    # ============================================
    try:
        pipeline = get_correction_pipeline()
        
        # Construire le texte comme dans PyQt
        text_to_process = text
        if location:
            text_to_process = f"{text} - Localisation: {location}"
        
        # Appeler le pipeline (comme dans PyQt - CorrectionWorker)
        resultat = pipeline.corriger_observation(
            observation_brute=text_to_process,
            k_documents=3
        )
        
        # Vérifier le statut (comme dans PyQt - on_reformulation_ready)
        if resultat.get("statut") == "SUCCESS":
            observation_corrigee = resultat.get("observation_corrigee", text)
            source = "correction_pipeline_llm"
            logger.info(f"✅ Reformulation LLM réussie")
        else:
            # Fallback manuel
            logger.warning(f"⚠️ Pipeline échoué: {resultat.get('erreur')}")
            observation_corrigee = text
            source = "fallback_manual"
        
    except HTTPException:
        logger.warning("⚠️ CorrectionPipeline non disponible")
        observation_corrigee = text
        source = "pipeline_unavailable"
    except Exception as e:
        logger.error(f"❌ Erreur CorrectionPipeline: {e}")
        observation_corrigee = text
        source = "error_fallback"
    
    # Ajouter localisation SI elle n'est pas déjà dans le texte
    if location and "Localisation:" not in observation_corrigee:
        observation_corrigee += f" - Localisation: {location}"
    
    # Ajouter thème SI spécifié
    if theme_filter:
        observation_corrigee += f" [Thème: {theme_filter}]"
    
    # ============================================
    # 2. ANALYSE DE GRAVITÉ (comme PyQt)
    # ============================================
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['dénudé', 'dangereux', 'risque', 'urgence', 'incendie', 'étincelle']):
        niveau_gravite = "Élevée"
        delai_recommande = "24-48 heures"
    elif any(word in text_lower for word in ['défectueux', 'chaud', 'anormal', 'fumée']):
        niveau_gravite = "Moyenne"
        delai_recommande = "1 semaine"
    else:
        niveau_gravite = "Basse"
        delai_recommande = "1 mois"
    
    # ============================================
    # 3. RÉFÉRENCES NORMATIVES
    # ============================================
    references_normatives = ["NFC 15-100 - Installations électriques basse tension"]
    
    if any(word in text_lower for word in ['cable', 'câble', 'fil', 'conducteur']):
        references_normatives.append("NFC 32-321 - Câbles électriques")
    if any(word in text_lower for word in ['disjoncteur', 'différentiel', 'protection', 'ddr']):
        references_normatives.append("NFC 14-100 - Dispositifs de protection")
    if any(word in text_lower for word in ['prise', 'terre', 'masse']):
        references_normatives.append("NFC 15-551 - Mise à la terre")
    if any(word in text_lower for word in ['tableau', 'coffret']):
        references_normatives.append("NFC 15-100 - Article 537 (Tableaux)")
    if any(word in text_lower for word in ['luminaire', 'éclairage', 'lampe']):
        references_normatives.append("NFC 15-100 - Article 771 (Éclairage)")
    
    # Ajouter thème aux références si présent
    if theme_filter and _theme_searcher_instance:
        try:
            matching_themes = _theme_searcher_instance.search_themes(theme_filter)
            if matching_themes:
                references_normatives.append(f"Thèmes: {', '.join(matching_themes[:3])}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur recherche thèmes: {e}")
    
    # ============================================
    # 4. EXTRACTION DE NORME (comme PyQt - extract_art_libelle)
    # ============================================
    norme_applicable = "NFC 15-100"
    try:
        prescriptions = get_prescriptions()
        if prescriptions and len(prescriptions) > 0:
            # Utiliser la fonction comme dans PyQt
            from core.norme_lookup import get_norme_from_db
            norme_result = get_norme_from_db(text, prescriptions)
            
            # Vérifier que c'est une vraie norme
            if norme_result and "❌" not in norme_result and "Aucune norme" not in norme_result:
                norme_applicable = norme_result
            else:
                logger.info(f"📚 Norme par défaut utilisée (résultat: {norme_result[:50] if norme_result else 'None'}...)")
    except Exception as e:
        logger.warning(f"⚠️ Erreur extraction norme: {e}")
    
    # ============================================
    # 5. CONSTRUCTION DE LA RÉPONSE
    # ============================================
    logger.info(f"✅ Reformulation terminée: gravité={niveau_gravite}, source={source}")
    
    return ReformulateResponse(
        observation_corrigee=observation_corrigee,
        niveau_gravite=niveau_gravite,
        delai_recommande=delai_recommande,
        references_normatives=references_normatives,
        norme_applicable=norme_applicable,
        source=source,
        theme_filter_applied=theme_filter if theme_filter else None
    )

@router.post("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(request: AutocompleteRequest):
    """
    Autocomplétion intelligente avec filtrage par thème
    Similaire à la méthode get_suggestions de MainWindow
    """
    logger.info(f"🔍 Autocomplete: '{request.query}' (theme: {request.theme_filter})")
    
    try:
        engine = get_suggestion_engine()
        
        if len(request.query.strip()) < 3:
            return AutocompleteResponse(
                query=request.query,
                suggestions=[],
                count=0,
                theme_filter=request.theme_filter
            )
        
        matching_themes = []
        
        # Filtrer par thème si spécifié
        if request.theme_filter and _theme_searcher_instance:
            matching_themes = _theme_searcher_instance.search_themes(request.theme_filter)
            logger.info(f"🎯 Thèmes correspondants: {matching_themes}")
        
        # Obtenir les suggestions
        all_suggestions = engine.get_suggestions(
            user_input=request.query,
            max_suggestions=request.max_results * 2
        )
        
        # Filtrer par thème si nécessaire
        filtered_suggestions = _filter_suggestions_by_theme(
            all_suggestions, 
            matching_themes, 
            request.max_results
        )
        
        logger.info(f"✅ {len(filtered_suggestions)} suggestions trouvées")
        
        return AutocompleteResponse(
            query=request.query,
            suggestions=filtered_suggestions,
            count=len(filtered_suggestions),
            theme_filter=request.theme_filter,
            matching_themes=matching_themes if matching_themes else None
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur autocomplete: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract_norme", response_model=NormeResponse)
async def extract_norme_endpoint(request: NormeRequest):
    """
    Extraire la norme NFC 15-100 correspondante
    Similaire à la méthode extract_art_libelle de MainWindow
    """
    logger.info(f"📚 Extraction norme: '{request.observation[:50]}...'")
    
    try:
        if not request.observation.strip():
            return NormeResponse(
                norme="Observation vide",
                confidence=0.1,
                theme_filter=request.theme_filter
            )
        
        norme = _extract_norme(request.observation)
        confidence = 0.85 if "NFC" in norme else 0.5
        
        # Ajouter contexte thème si présent
        if request.theme_filter:
            norme += f" [Filtre: {request.theme_filter}]"
        
        return NormeResponse(
            norme=norme,
            confidence=confidence,
            theme_filter=request.theme_filter
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur extraction norme: {e}")
        return NormeResponse(
            norme="NFC 15-100 - Erreur technique",
            confidence=0.1,
            theme_filter=request.theme_filter
        )


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Recherche sémantique dans les documents
    Avec filtrage par thème optionnel
    """
    try:
        logger.info(f"🔍 Recherche: '{request.query}' (theme: {request.theme_filter})")
        
        vector_store = get_vector_store()
        
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query vide")
        
        matching_themes = []
        filtered_results = []
        
        # Filtrer par thème si spécifié
        if request.theme_filter and _theme_searcher_instance:
            matching_themes = _theme_searcher_instance.search_themes(request.theme_filter)
            
            if matching_themes:
                # Récupérer les documents par thème
                theme_docs = []
                for theme in matching_themes:
                    docs = _theme_searcher_instance.get_theme_documents(theme, request.max_results * 3)
                    theme_docs.extend(docs)
                
                # Recherche dans tous les docs
                all_results = vector_store.search(request.query, k=request.max_results * 5)
                
                # Filtrer
                theme_doc_ids = {id(doc) for doc in theme_docs}
                filtered_results = [
                    doc for doc in all_results 
                    if id(doc) in theme_doc_ids
                ][:request.max_results]
        
        if not filtered_results:
            filtered_results = vector_store.search(query=request.query, k=request.max_results)
        
        # Formater les résultats
        formatted_results = []
        for i, result in enumerate(filtered_results):
            metadata = {}
            content = ""
            score = 0.85 - (i * 0.05)
            
            if hasattr(result, 'metadata'):
                metadata = result.metadata
                content = result.page_content if hasattr(result, 'page_content') else str(result)
            elif isinstance(result, dict):
                metadata = result.get("metadata", {})
                content = result.get("content", str(result))
                score = result.get("score", score)
            else:
                content = str(result)
                metadata = {"source": "vector_store"}
            
            formatted_results.append(SearchResult(
                content=content[:300] + "..." if len(content) > 300 else content,
                metadata=metadata,
                score=min(max(score, 0.0), 1.0),
                source=metadata.get("ART_LIBELLE", metadata.get("source")),
                theme=metadata.get("Thème", "Inconnu")
            ))
        
        logger.info(f"✅ {len(formatted_results)} documents trouvés")
        
        return SearchResponse(
            query=request.query,
            results=formatted_results,
            count=len(formatted_results),
            theme_filter=request.theme_filter,
            matching_themes=matching_themes if matching_themes else None
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS DE GESTION DES THÈMES
# ============================================================================

@router.post("/themes/search", tags=["thèmes"])
async def search_themes(request: ThemeSearchRequest):
    """Rechercher des thèmes par expression partielle"""
    try:
        logger.info(f"🎯 Search themes: '{request.query}'")
        
        if not _theme_searcher_instance:
            raise HTTPException(status_code=503, detail="ThemeSearcher non disponible")
        
        matches = _theme_searcher_instance.search_themes(
            request.query, 
            min_similarity=request.min_similarity
        )
        
        themes_with_stats = []
        for theme in matches:
            doc_count = len(_theme_searcher_instance.get_theme_documents(theme))
            themes_with_stats.append({
                "theme": theme,
                "doc_count": doc_count,
                "documents_sample": [
                    doc.get("content", "")[:100] + "..."
                    for doc in _theme_searcher_instance.get_theme_documents(theme, 3)
                ]
            })
        
        return {
            "query": request.query,
            "min_similarity": request.min_similarity,
            "themes": themes_with_stats,
            "total_matches": len(matches)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur recherche thèmes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/themes/suggest", tags=["thèmes"])
async def suggest_themes(request: ThemeSuggestRequest):
    """Suggérer des thèmes pour l'autocomplétion"""
    try:
        logger.info(f"💡 Suggest themes: '{request.partial_query}'")
        
        if not _theme_searcher_instance:
            raise HTTPException(status_code=503, detail="ThemeSearcher non disponible")
        
        suggestions = _theme_searcher_instance.suggest_themes(
            request.partial_query, 
            max_suggestions=request.max_suggestions
        )
        
        return {
            "partial_query": request.partial_query,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur suggestions thèmes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes/available", tags=["thèmes"])
async def get_available_themes():
    """Lister tous les thèmes disponibles"""
    try:
        logger.info("📋 Get available themes")
        
        if not _theme_searcher_instance:
            raise HTTPException(status_code=503, detail="ThemeSearcher non disponible")
        
        themes = _theme_searcher_instance.get_available_themes()
        stats = _theme_searcher_instance.get_theme_stats()
        
        return {
            "themes": themes,
            "stats": stats,
            "total_themes": len(themes),
            "total_documents": sum(stats.values())
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur liste thèmes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/themes/stats", tags=["thèmes"])
async def get_themes_stats():
    """Obtenir les statistiques des thèmes"""
    try:
        logger.info("📊 Get themes stats")
        
        if not _theme_searcher_instance:
            raise HTTPException(status_code=503, detail="ThemeSearcher non disponible")
        
        stats = _theme_searcher_instance.get_theme_stats()
        
        sorted_stats = dict(
            sorted(stats.items(), key=lambda x: x[1], reverse=True)
        )
        
        return {
            "stats": sorted_stats,
            "total_themes": len(stats),
            "total_documents": sum(stats.values()),
            "most_common": list(sorted_stats.items())[:10] if stats else []
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur stats thèmes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS DE MONITORING
# ============================================================================

@router.get("/status")
async def get_status():
    """Statut détaillé du système"""
    
    prescriptions_count = 0
    if _prescriptions_instance is not None:
        if isinstance(_prescriptions_instance, list):
            prescriptions_count = len(_prescriptions_instance)
        elif isinstance(_prescriptions_instance, dict):
            prescriptions_count = len(_prescriptions_instance)
    
    vector_docs = 0
    if _vector_store_instance is not None:
        if hasattr(_vector_store_instance, 'index'):
            vector_docs = _vector_store_instance.index.ntotal
    
    theme_info = {}
    if _theme_searcher_instance:
        theme_info = {
            "available_themes": len(_theme_searcher_instance.get_available_themes()),
            "total_documents": sum(_theme_searcher_instance.get_theme_stats().values())
        }
    
    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "suggestion_engine": _suggestion_engine_instance is not None,
            "correction_pipeline": _correction_pipeline_instance is not None,
            "vector_store": _vector_store_instance is not None,
            "prescriptions_loaded": prescriptions_count > 0,
            "theme_searcher": _theme_searcher_instance is not None
        },
        "stats": {
            "prescriptions_count": prescriptions_count,
            "vector_store_docs": vector_docs,
            "theme_searcher": theme_info,
            "api_version": "2.0.0",
            "system": "RAG API - Normes Électriques"
        }
    }


@router.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    services_ready = (
        _suggestion_engine_instance is not None and 
        _vector_store_instance is not None
    )
    
    return {
        "status": "healthy" if services_ready else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "suggestion_engine": _suggestion_engine_instance is not None,
            "vector_store": _vector_store_instance is not None,
            "correction_pipeline": _correction_pipeline_instance is not None,
            "theme_searcher": _theme_searcher_instance is not None
        }
    }


# ============================================================================
# FONCTIONS UTILITAIRES PRIVÉES
# ============================================================================

def _reformulation_manuelle_intelligente(observation: str) -> str:
    """
    Reformulation manuelle intelligente si le LLM échoue
    Inspiré de la logique de MainWindow
    """
    obs_lower = observation.lower()
    
    # Identifier le verbe d'action
    verbes = {
        'remplacer': ['remplacer', 'changer', 'échanger'],
        'installer': ['installer', 'mettre', 'poser', 'monter'],
        'vérifier': ['vérifier', 'contrôler', 'tester', 'inspecter'],
        'réparer': ['réparer', 'corriger', 'fixer'],
        'nettoyer': ['nettoyer', 'dégager', 'enlever'],
        'sécuriser': ['sécuriser', 'protéger'],
        'modifier': ['modifier', 'adapter', 'ajuster']
    }
    
    verbe = "Corriger"
    for v, keywords in verbes.items():
        if any(kw in obs_lower for kw in keywords):
            verbe = v.capitalize()
            break
    
    # Identifier l'objet
    objets = {
        'prise': ('la prise de courant', ['prise']),
        'disjoncteur': ('le disjoncteur différentiel', ['disjoncteur', 'ddr']),
        'câble': ('les câbles électriques', ['câble', 'cable', 'fil']),
        'luminaire': ('le luminaire', ['luminaire', 'éclairage']),
        'tableau': ('le tableau électrique', ['tableau', 'coffret']),
        'terre': ('la liaison équipotentielle', ['terre', 'masse']),
        'interrupteur': ("l'interrupteur", ['interrupteur']),
        'protection': ('la protection électrique', ['protection'])
    }
    
    objet = "l'installation électrique"
    detail = "non conforme"
    
    for obj_key, (obj_name, keywords) in objets.items():
        if any(kw in obs_lower for kw in keywords):
            objet = obj_name
            detail = ""
            
            # Détails spécifiques
            if obj_key == 'prise' and 'terre' in obs_lower:
                detail = "pour assurer la mise à la terre"
            elif obj_key == 'disjoncteur':
                if '30ma' in obs_lower or '30 ma' in obs_lower:
                    detail = "30mA"
                elif 'type a' in obs_lower:
                    detail = "de type A"
            elif obj_key == 'câble' and 'dénudé' in obs_lower:
                detail = "présentant des conducteurs dénudés"
            break
    
    # Construire la phrase
    phrase = f"{verbe} {objet}"
    if detail:
        phrase += f" {detail}"
    
    # Nettoyer
    phrase = ' '.join(phrase.split())
    if phrase and phrase[0].islower():
        phrase = phrase[0].upper() + phrase[1:]
    
    return phrase


def _get_references_normatives(text: str, theme_filter: Optional[str] = None) -> List[str]:
    """Générer les références normatives appropriées"""
    refs = ["NFC 15-100 - Installations électriques basse tension"]
    
    text_lower = text.lower()
    
    mapping = {
        'cable|câble|fil|conducteur': "NFC 32-321 - Câbles électriques",
        'disjoncteur|différentiel|protection|ddr': "NFC 14-100 - Dispositifs de protection",
        'prise|terre|masse': "NFC 15-551 - Mise à la terre",
        'tableau|coffret': "NFC 15-100 - Article 537 (Tableaux)",
        'luminaire|éclairage|lampe': "NFC 15-100 - Article 771 (Éclairage)"
    }
    
    for keywords, ref in mapping.items():
        if any(word in text_lower for word in keywords.split('|')):
            refs.append(ref)
    
    # Ajouter thème si présent
    if theme_filter and _theme_searcher_instance:
        try:
            matching_themes = _theme_searcher_instance.search_themes(theme_filter)
            if matching_themes:
                refs.append(f"Thèmes: {', '.join(matching_themes[:3])}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur ajout thème aux refs: {e}")
    
    return refs


def _extract_norme(observation: str) -> str:
    """Extraire la norme applicable"""
    try:
        prescriptions = get_prescriptions()
        
        if prescriptions and len(prescriptions) > 0:
            from core.norme_lookup import get_norme_from_db
            norme = get_norme_from_db(observation, prescriptions)
            
            if norme and "pas de norme" not in norme.lower() and "aucune norme" not in norme.lower():
                return norme
        
        # Fallback intelligent
        obs_lower = observation.lower()
        fallbacks = {
            'différentiel|disjoncteur': "NFC 14-100 - Dispositifs différentiels (Article 531.3.3)",
            'câble|fil|conducteur': "NFC 15-100 - Article 553.1.1 (Protection)",
            'prise|terre': "NFC 15-551 - Mise à la terre (Article 551.4)",
            'tableau': "NFC 15-100 - Article 537 (Tableaux de distribution)",
            'luminaire|éclairage': "NFC 15-100 - Article 771 (Éclairage)"
        }
        
        for keywords, norme in fallbacks.items():
            if any(word in obs_lower for word in keywords.split('|')):
                return norme
        
        return "NFC 15-100 - Article applicable à déterminer"
        
    except Exception as e:
        logger.error(f"❌ Erreur extraction norme: {e}")
        return "NFC 15-100 - Erreur technique"


def _filter_suggestions_by_theme(
    suggestions: List[str], 
    matching_themes: List[str], 
    max_results: int
) -> List[str]:
    """
    Filtrer les suggestions par thèmes correspondants
    Inspiré de ThemeFilteredSuggestionWorker
    """
    if not matching_themes or not _theme_searcher_instance:
        return suggestions[:max_results]
    
    filtered = []
    
    # Récupérer les documents par thème
    theme_docs = []
    for theme in matching_themes:
        docs = _theme_searcher_instance.get_theme_documents(theme, 50)
        theme_docs.extend(docs)
    
    # Créer un set des contenus
    theme_contents = {doc.get('content', '') for doc in theme_docs}
    theme_contents_normalized = {c.lower().strip() for c in theme_contents}
    
    # Filtrer les suggestions
    for suggestion in suggestions:
        suggestion_normalized = suggestion.lower().strip()
        
        # Vérifier si dans les documents du thème
        if suggestion in theme_contents or suggestion_normalized in theme_contents_normalized:
            filtered.append(suggestion)
            continue
        
        # Vérifier si contient des mots-clés du thème
        for theme in matching_themes:
            if theme.lower() in suggestion_normalized:
                filtered.append(suggestion)
                break
    
    # Si pas assez, ajouter des suggestions originales
    if len(filtered) < max_results // 2:
        for suggestion in suggestions:
            if suggestion not in filtered:
                filtered.append(suggestion)
                if len(filtered) >= max_results:
                    break
    
    return filtered[:max_results]