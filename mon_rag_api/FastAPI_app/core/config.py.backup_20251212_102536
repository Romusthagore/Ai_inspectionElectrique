"""
Configuration centralisée pour le projet RAG - Normes électriques
Version OPTIMISÉE pour correction automatique d'observations
"""
from groq_config import GroqLLMClient, AVAILABLE_MODELS
from pathlib import Path
import logging
import os

# =============================================================================
# CHEMINS ABSOLUS
# =============================================================================

BASE_DIR = Path("/home/student24/Downloads/Mes projets/PROJET RAPPORTS/My_project")

# CHEMINS PRINCIPAUX
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
SCRIPT_DIR = BASE_DIR / "script"
FAISS_INDEX_PATH = DATA_DIR / "index.faiss"
METADATA_PATH = DATA_DIR / "index.pkl"
DOCUMENTS_JSON_DIR = DATA_DIR / "document_json"
NORMES_DIR = DATA_DIR / "normes"

# =============================================================================
# CONFIGURATION EMBEDDINGS ET RAG
# =============================================================================

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

TOP_K = 5
SIMILARITY_THRESHOLD = 0.2
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
MAX_CONTEXT_TOKENS = 3000
MAX_CONTEXT_LENGTH = 4000

# =============================================================================
# CONFIGURATION LLM
# =============================================================================

DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"
LLM_MODEL = DEFAULT_LLM_MODEL  # Alias pour compatibilité
TEMPERATURE = 0.4

# =============================================================================
# LOGGING
# =============================================================================

LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# =============================================================================
# FONCTION LLM CLIENT
# =============================================================================

def get_llm_client(model: str = None, temperature: float = 0.4):
    """Retourne un client LLM configuré pour la correction d'observations"""
    try:
        client = GroqLLMClient(
            model=model or DEFAULT_LLM_MODEL,
            temperature=temperature
        )
        logger.info(f" LLM initialisé: {client.model}")
        return client
    except Exception as e:
        logger.error(f" Erreur initialisation LLM: {e}")
        return None

# =============================================================================
# PROMPTS SYSTÈME
# =============================================================================

SYSTEM_PROMPT = """Tu es un expert en normes électriques françaises NFC 15-100. 
Tu DOIS extraire les références normatives EXACTES pour chaque observation.

DIRECTIVES ABSOLUES:
1. IDENTIFIER les articles NFC 15-100 applicables
2. CITER les références COMPLÈTES (ex: "NFC 15-100 Article 55.1")
3. ÉVALUER la gravité selon la norme
4. PROPOSER des actions correctives normées
5. UTILISER la terminologie technique exacte """

# =============================================================================
# PROMPT POUR RAG
# =============================================================================

RAG_PROMPT_TEMPLATE = """
CONTEXTE DOCUMENTAIRE (extraits des normes électriques):
{context}

---

QUESTION/OBSERVATION:
{question}

---

INSTRUCTIONS DE RÉPONSE:
1. Analyse le contexte normatif fourni
2. Identifie les articles NFC 15-100 applicables  
3. Formule une réponse technique structurée
4. Cite les références exactes (ex: "NFC 15-100 Article 55.1")
5. Sois concis et précis

RÉPONSE TECHNIQUE:
"""

# =============================================================================
# PROMPT POUR CORRECTION D'OBSERVATIONS
# =============================================================================

CORRECTION_PROMPT = """
OBSERVATION BRUTE À CORRIGER :
{observation_brute}

CONTEXTE NORMATIF :
{context}

INSTRUCTIONS CRITIQUES :
1. **ANALYSE DE DANGER** : Évaluez sérieusement les risques (fils dénudés = CRITIQUE, odeur brûlé = URGENT)
2. **NE PAS MINIMISER** : Une odeur de brûlé avec fils dénudés n'est JAMAIS "Mineur"
3. **OBSERVATION COMPLÈTE** : La reformulation doit être détaillée et technique

RÉPONSE ATTENDUE EN JSON :
{{
  "observation_corrigee": "Description technique complète des anomalies identifiées",
  "niveau_gravite": "Critique|Majeur|Mineur",
  "delai_recommande": "Immédiat|24h|7 jours|30 jours",
  "references_normatives": ["NFC 15-100 Art. XYZ", ...],
  "risques_identifies": ["Liste des risques spécifiques"],
  "actions_correctives": ["Actions prioritaires"],
  "localisation": "Localisation si précisée"
}}
"""

# Alias pour compatibilité avec ancien code
OBSERVATION_PROMPT = CORRECTION_PROMPT

# =============================================================================
# CATÉGORIES ET TEMPLATES
# =============================================================================

CATEGORIES_OBSERVATIONS = {
    "protection_différentielle": {
        "keywords": ["différentiel", "DDR", "30mA", "disjoncteur"],
        "normes": ["NF C 15-100", "Article 55"],
        "gravité_par_défaut": "Majeur"
    },
    "mise_à_la_terre": {
        "keywords": ["terre", "prise terre", "liaison équipotentielle"],
        "normes": ["NF C 15-100", "Article 54"], 
        "gravité_par_défaut": "Critique"
    },
    "circuits_prises": {
        "keywords": ["prise", "socle", "courant"],
        "normes": ["NF C 15-100", "Article 55"],
        "gravité_par_défaut": "Majeur"
    },
    "protection_foudre": {
        "keywords": ["paratonnerre", "foudre", "ARF"],
        "normes": ["NF EN 62305-2", "NF C 17-102"],
        "gravité_par_défaut": "Critique"
    },
    "mesures_contrôles": {
        "keywords": ["isolement", "mesure", "contrôle", "essai"],
        "normes": ["UTE C 15-105", "NF C 15-100"],
        "gravité_par_défaut": "Mineur"
    }
}

TEMPLATE_OBSERVATION_STANDARD = """
**OBSERVATION** : {observation}
**LOCALISATION** : {localisation}
**RÉFÉRENCE** : {reference}
**GRAVITÉ** : {gravite}
**ACTION** : {action}
"""

# =============================================================================
# CHEMINS VERS FICHIERS DE DONNÉES
# =============================================================================

NORMES_JSON_PATH = DOCUMENTS_JSON_DIR / "normes_articles.json"
CORRESPONDANCES_PATH = DOCUMENTS_JSON_DIR / "correspondances_normatives.json"

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def detecter_categorie(observation: str) -> str:
    """Détecte la catégorie technique d'une observation"""
    observation_lower = observation.lower()
    for categorie, config in CATEGORIES_OBSERVATIONS.items():
        if any(keyword in observation_lower for keyword in config["keywords"]):
            return categorie
    return "général"

def get_config_categorie(categorie: str) -> dict: # TRES IPORTANT
    """Retourne la configuration d'une catégorie"""
    return CATEGORIES_OBSERVATIONS.get(categorie, {
        "normes": ["NF C 15-100"],
        "gravité_par_défaut": "Mineur"
    })

def initialiser_repertoires():
    """Crée les répertoires nécessaires"""
    repertoires = [DATA_DIR, MODELS_DIR, SCRIPT_DIR, DOCUMENTS_JSON_DIR, NORMES_DIR]
    for repertoire in repertoires:
        repertoire.mkdir(parents=True, exist_ok=True)
    logger.info("✅ Répertoires initialisés")

def valider_configuration():
    """Validation de la configuration"""
    errors = []
    
    if not DATA_DIR.exists():
        errors.append(f"DATA_DIR introuvable: {DATA_DIR}")
    
    if not FAISS_INDEX_PATH.exists():
        logger.warning(f"Index FAISS introuvable: {FAISS_INDEX_PATH}")
    
    if errors:
        raise ValueError("\n".join(errors))
    
    logger.info(" Configuration validée")
    return True

# =============================================================================
# EXPORT DES VARIABLES
# =============================================================================

__all__ = [
    # Chemins
    "BASE_DIR", "DATA_DIR", "MODELS_DIR", "SCRIPT_DIR",
    "FAISS_INDEX_PATH", "METADATA_PATH", "DOCUMENTS_JSON_DIR", "NORMES_DIR",
    "NORMES_JSON_PATH", "CORRESPONDANCES_PATH",
    
    # Configuration embeddings
    "EMBEDDING_MODEL", "EMBEDDING_DIMENSION",
    
    # Paramètres RAG
    "TOP_K", "MAX_CONTEXT_TOKENS", "SIMILARITY_THRESHOLD",
    "CHUNK_SIZE", "CHUNK_OVERLAP", "MAX_CONTEXT_LENGTH",
    
    # LLM
    "get_llm_client", "DEFAULT_LLM_MODEL", "LLM_MODEL", "TEMPERATURE",
    
    # Prompts
    "SYSTEM_PROMPT", "CORRECTION_PROMPT", "OBSERVATION_PROMPT", "RAG_PROMPT_TEMPLATE",
    
    # Catégories et templates
    "CATEGORIES_OBSERVATIONS", "TEMPLATE_OBSERVATION_STANDARD",
    "detecter_categorie", "get_config_categorie",
    
    # Utilitaires
    "valider_configuration", "initialiser_repertoires",
    
    # Logger
    "logger"
]

# =============================================================================
# INITIALISATION AU CHARGEMENT DU MODULE
# =============================================================================

if __name__ != "__main__":
    # Initialisation silencieuse au chargement du module
    try:
        initialiser_repertoires()
        valider_configuration()
    except Exception as e:
        logger.warning(f" Avertissement initialisation: {e}")