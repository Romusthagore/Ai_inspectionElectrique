from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv
from datetime import datetime  

# Charge les variables d'environnement
load_dotenv()

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables globales
suggestion_engine = None
vector_store = None
correction_pipeline = None
prescriptions = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    global suggestion_engine, vector_store, correction_pipeline, prescriptions
    
    # Startup
    logger.info("🚀 Démarrage des services RAG...")
    
    try:
        # Import ici pour éviter les imports circulaires
        from core.vector_store import get_vector_store
        from core.groq_config import get_llm
        from core.suggestion_engine import SuggestionEngine
        from core.correction_pipeline import CorrectionPipeline
        from core.prescription_loader import load_prescriptions
        
        # 1. VectorStore
        vector_store = get_vector_store()
        logger.info(f"✅ VectorStore: {vector_store.index.ntotal} vecteurs")
        
        # 2. LLM
        llm = get_llm()
        logger.info(f"✅ LLM chargé: {llm.model_name}")
        
        # 3. SuggestionEngine
        suggestion_engine = SuggestionEngine(
            vectorstore=vector_store,
            llm=llm,
            k_documents=30,
            min_similarity=0.65
        )
        logger.info("✅ SuggestionEngine initialisé")
        
        # 4. CorrectionPipeline
        correction_pipeline = CorrectionPipeline(llm=llm)
        logger.info("✅ CorrectionPipeline initialisé")
        
        # 5. Prescriptions
        prescriptions = load_prescriptions()
        logger.info(f"✅ Prescriptions chargées: {len(prescriptions)} éléments")
        
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Ne pas raise pour permettre au serveur de démarrer quand même
    
    yield  # L'application tourne ici
    
    # Shutdown
    logger.info("👋 Arrêt des services RAG...")

# Création de l'app FastAPI UNE SEULE FOIS
app = FastAPI(
    title="RAG API - Normes Électriques",
    description="API d'autocomplétion pour normes NFC 15-100",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS - ajoutez-le à l'instance existante
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour le développement, autoriser toutes les origines
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Routes de base
@app.get("/")
def root():
    return {
        "message": "API RAG Normes Électriques NFC 15-100",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "autocomplete": "POST /api/v1/autocomplete",
            "reformulate": "POST /api/v1/reformulate",
            "extract_norme": "POST /api/v1/extract_norme",
            "search": "POST /api/v1/search",
            "health": "GET /health",
            "test": "GET /test",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engine_ready": suggestion_engine is not None,
        "vector_store_ready": vector_store is not None,
        "correction_pipeline_ready": correction_pipeline is not None,
        "prescriptions_ready": prescriptions is not None and len(prescriptions) > 0,
        "groq_api_key": bool(os.getenv("GROQ_API_KEY")),
        "services": {
            "vector_store_count": vector_store.index.ntotal if vector_store else 0,
            "prescriptions_count": len(prescriptions) if prescriptions else 0
        }
    }

@app.get("/test")
@app.get("/api/v1/test")
async def test_endpoint():
    return {
        "message": "✅ API FastAPI fonctionne parfaitement !",
        "status": "ready",
        "server": "192.168.0.217:8000",
        "timestamp": datetime.now().isoformat(),
        "cors": "enabled",
        "endpoints": {
            "health": "GET /health",
            "test": "GET /test", 
            "test_api": "GET /api/v1/test",
            "autocomplete": "POST /api/v1/autocomplete",
            "reformulate": "POST /api/v1/reformulate",
            "extract_norme": "POST /api/v1/extract_norme",
            "search": "POST /api/v1/search",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

# Inclure les routes API avec gestion d'erreur
try:
    # Injecter les services dans le module api.endpoints
    import api.endpoints
    api.endpoints.suggestion_engine = suggestion_engine
    api.endpoints.vector_store = vector_store
    api.endpoints.correction_pipeline = correction_pipeline
    api.endpoints.prescriptions = prescriptions
    
    from api.endpoints import router as api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("✅ Routes API incluses avec succès")
    
    # Vérifier les routes disponibles
    logger.info("======================================================================")
    logger.info("📍 Routes disponibles après inclusion:")
    for route in app.routes:
        logger.info(f"   {route.methods} {route.path}")
    logger.info(f"📊 Total: {len(app.routes)} routes enregistrées")
    logger.info("======================================================================")
    
except Exception as e:
    logger.error(f"❌ Erreur chargement routes API: {e}")
    import traceback
    logger.error(traceback.format_exc())
    # Le serveur démarre quand même sans les routes API