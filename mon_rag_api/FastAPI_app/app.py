#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Application - RAG API pour Normes Électriques
AVEC FILTRAGE PAR THÈME
"""

# ============================================================================
# CONFIGURATION UTF-8 CRITIQUE - DOIT ÊTRE EN PREMIER !
# ============================================================================
import sys
import os
import locale

# Force UTF-8 partout AVANT tous les autres imports
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'

try:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
except:
    pass

# Force stdout/stderr en UTF-8
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# MAINTENANT on peut importer le reste
# ============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
import traceback

# Charge les variables d'environnement
load_dotenv()

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables globales
suggestion_engine = None
vector_store = None
correction_pipeline = None
theme_searcher = None
prescriptions = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application AVEC THEME_SEARCHER"""
    global suggestion_engine, vector_store, correction_pipeline, theme_searcher, prescriptions
    
    # Startup
    logger.info("🚀 Démarrage des services RAG AVEC FILTRAGE PAR THÈME...")
    
    try:
        # 1. VectorStore
        from core.vector_store import get_vector_store
        vector_store = get_vector_store()
        
        if hasattr(vector_store, 'index'):
            logger.info(f"✅ VectorStore: {vector_store.index.ntotal} vecteurs")
        
        # 2. CorrectionPipeline
        from core.correction_pipeline import get_correction_pipeline
        correction_pipeline = get_correction_pipeline()
        
        # 3. Extraire le LLM
        if hasattr(correction_pipeline, 'llm'):
            llm = correction_pipeline.llm
        else:
            llm = correction_pipeline._llm
        
        logger.info(f"✅ LLM extrait: {llm.model_name if hasattr(llm, 'model_name') else type(llm).__name__}")
        
        # 4. SuggestionEngine
        from core.suggestion_engine import get_suggestion_engine
        suggestion_engine = get_suggestion_engine(
            vectorstore=vector_store,
            llm=llm
        )
        
        # 5. ThemeSearcher
        try:
            from core.theme_searcher import get_theme_searcher
            theme_searcher = get_theme_searcher(vectorstore=vector_store)
            if theme_searcher:
                themes_count = len(theme_searcher.get_available_themes())
                logger.info(f"✅ ThemeSearcher: {themes_count} thèmes disponibles")
            else:
                logger.warning("⚠️ ThemeSearcher non initialisé")
        except ImportError as e:
            logger.warning(f"⚠️ Module theme_searcher non disponible: {e}")
            theme_searcher = None
        
        # 6. Vérifications
        if hasattr(suggestion_engine, 'tous_les_verbes'):
            logger.info(f"✅ SuggestionEngine: {len(suggestion_engine.tous_les_verbes)} verbes chargés")
        
        # 7. Récupérer les prescriptions
        if hasattr(vector_store, 'metadata_store'):
            prescriptions = vector_store.metadata_store
        elif hasattr(vector_store, 'metadata'):
            prescriptions = vector_store.metadata
        else:
            logger.warning("⚠️ Aucune prescription trouvée dans vector_store")
            prescriptions = []
        
        logger.info(f"📊 Prescriptions: {len(prescriptions)} éléments")
        
        # 8. Injecter dans endpoints
        from api.endpoints import (
            set_suggestion_engine, 
            set_vector_store,
            set_correction_pipeline,
            set_prescriptions,
            set_theme_searcher
        )
        
        set_suggestion_engine(suggestion_engine)
        set_vector_store(vector_store)
        set_correction_pipeline(correction_pipeline)
        set_prescriptions(prescriptions)
        set_theme_searcher(theme_searcher)
        
        logger.info(f"✅ Prescriptions injectées: {len(prescriptions)} éléments")
        logger.info("✅ Services injectés dans api.endpoints")
        logger.info("✅ Tous les services initialisés")
        
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        traceback.print_exc()
    
    yield
    
    # Shutdown
    logger.info("👋 Arrêt des services RAG...")

# ============================================================================
# CRÉATION DE L'APPLICATION
# ============================================================================

app = FastAPI(
    title="RAG API - Normes Électriques",
    description="API d'autocomplétion pour normes NFC 15-100 AVEC FILTRAGE PAR THÈME",
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "autocomplete",
            "description": "Autocomplétion intelligente avec filtrage par thème"
        },
        {
            "name": "reformulation",
            "description": "Reformulation d'observations électriques"
        },
        {
            "name": "recherche",
            "description": "Recherche sémantique dans les normes"
        },
        {
            "name": "thèmes",
            "description": "Recherche et filtrage par thème"
        }
    ]
)

logger.info(f"✅ Application FastAPI créée: {app.title}")

# ============================================================================
# MIDDLEWARE CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTES DE BASE
# ============================================================================

@app.get("/")
def root():
    """Page d'accueil de l'API"""
    return {
        "message": "API RAG Normes Électriques NFC 15-100",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "autocomplete",
            "reformulation",
            "norme_extraction",
            "semantic_search",
            "theme_filtering"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "api_health": "/api/v1/health",
            "api_status": "/api/v1/status",
            "autocomplete": "POST /api/v1/autocomplete",
            "search": "POST /api/v1/search",
            "reformulate": "POST /api/v1/reformulate",
            "extract_norme": "POST /api/v1/extract_norme",
            "themes_search": "POST /api/v1/themes/search",
            "themes_suggest": "POST /api/v1/themes/suggest",
            "themes_available": "GET /api/v1/themes/available",
            "themes_stats": "GET /api/v1/themes/stats"
        }
    }


@app.get("/health")
def health_check():
    """Check de santé global"""
    return {
        "status": "healthy",
        "engine_ready": suggestion_engine is not None,
        "vector_store_ready": vector_store is not None,
        "correction_pipeline_ready": correction_pipeline is not None,
        "theme_searcher_ready": theme_searcher is not None,
        "prescriptions_ready": len(prescriptions) > 0,
        "groq_api_key": bool(os.getenv("GROQ_API_KEY"))
    }


# ============================================================================
# INCLUSION DU ROUTER API
# ============================================================================

try:
    from api.endpoints import router
    
    app.include_router(router)
    
    logger.info("=" * 70)
    logger.info("✅ ROUTER API INCLUS AVEC SUCCÈS")
    logger.info("=" * 70)
    logger.info("📍 Routes disponibles:")
    logger.info("   POST /api/v1/autocomplete      - Autocomplétion intelligente AVEC THÈME")
    logger.info("   POST /api/v1/reformulate       - Reformulation d'observation AVEC THÈME")
    logger.info("   POST /api/v1/extract_norme     - Extraction de norme")
    logger.info("   POST /api/v1/search            - Recherche sémantique AVEC THÈME")
    logger.info("   GET  /api/v1/status            - Statut des services")
    logger.info("   GET  /api/v1/health            - Santé de l'API")
    logger.info("   POST /api/v1/themes/search     - Recherche de thèmes")
    logger.info("   POST /api/v1/themes/suggest    - Suggestions de thèmes")
    logger.info("   GET  /api/v1/themes/available  - Thèmes disponibles")
    logger.info("   GET  /api/v1/themes/stats      - Statistiques des thèmes")
    logger.info("=" * 70)
    
except ImportError as e:
    logger.error("=" * 70)
    logger.error(f"❌ ERREUR: Module api.endpoints non trouvé")
    logger.error(f"   {e}")
    logger.error("   Vérifiez que le fichier api/endpoints.py existe")
    logger.error("=" * 70)
    
except Exception as e:
    logger.error("=" * 70)
    logger.error(f"❌ ERREUR lors de l'inclusion du router:")
    logger.error(f"   {e}")
    logger.error("=" * 70)
    traceback.print_exc()


# ============================================================================
# AFFICHAGE DE TOUTES LES ROUTES
# ============================================================================

@app.on_event("startup")
async def log_routes():
    """Logger les routes disponibles au démarrage"""
    logger.info("🔍 Vérification des routes enregistrées:")
    route_count = 0
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            logger.info(f"   {methods:8} {route.path}")
            route_count += 1

    logger.info(f"📊 Total: {route_count} routes enregistrées")


# ============================================================================
# FONCTIONS HELPER
# ============================================================================

def get_suggestion_engine():
    return suggestion_engine

def get_vector_store():
    return vector_store

def get_correction_pipeline():
    return correction_pipeline

def get_theme_searcher():
    return theme_searcher

def get_prescriptions():
    return prescriptions


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)