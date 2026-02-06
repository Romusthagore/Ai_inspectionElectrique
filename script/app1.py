print("1. Début du fichier")

from fastapi import FastAPI
print("2. FastAPI importé")

from fastapi.middleware.cors import CORSMiddleware
print("3. CORS importé")

from contextlib import asynccontextmanager
print("4. asynccontextmanager importé")

import logging
import os
from dotenv import load_dotenv
print("5. Autres imports OK")

load_dotenv()
print("6. .env chargé")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
print("7. Logging configuré")

suggestion_engine = None
vector_store = None
print("8. Variables globales initialisées")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("9. Fonction lifespan définie")
    global suggestion_engine, vector_store
    logger.info("🚀 Démarrage des services RAG...")
    
    try:
        from core.vector_store import get_vector_store
        from core.groq_config import get_llm
        from core.suggestion_engine import SuggestionEngine
        
        vector_store = get_vector_store()
        logger.info(f"✅ VectorStore: {vector_store.index.ntotal} vecteurs")
        
        llm = get_llm()
        logger.info(f"✅ LLM chargé: {llm.model_name}")
        
        suggestion_engine = SuggestionEngine(
            vectorstore=vector_store,
            llm=llm,
            k_documents=30,
            min_similarity=0.65
        )
        logger.info("✅ SuggestionEngine initialisé")
        
    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
    
    yield
    logger.info("👋 Arrêt des services RAG...")

print("10. Avant création app")

app = FastAPI(
    title="RAG API - Normes Électriques",
    description="API d'autocomplétion pour normes NFC 15-100",
    version="1.0.0",
    lifespan=lifespan
)

print("11. App créée!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("12. Middleware ajouté")

@app.get("/")
def root():
    return {
        "message": "API RAG Normes Électriques NFC 15-100",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "engine_ready": suggestion_engine is not None,
        "vector_store_ready": vector_store is not None,
        "groq_api_key": bool(os.getenv("GROQ_API_KEY"))
    }

print("13. Routes définies")

try:
    from api.endpoints import router as api_router
    app.include_router(api_router, prefix="/api/v1")
    print("14. Routes API incluses")
except Exception as e:
    print(f"14. Erreur routes API: {e}")

print("15. FIN DU FICHIER - app existe!")