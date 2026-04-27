 mon_rag_api/README.md
markdown
# RAG API - Documentation Technique

API REST d'autocomplétion, reformulation et recherche sémantique pour les normes électriques **NFC 15-100**, basée sur le **RAG (Retrieval-Augmented Generation)**.

---

## 🚀 Démarrage rapide

```bash
# 1. Aller dans le dossier de l'API
cd FastAPI_app

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer la clé API
# Créer .env avec : GROQ_API_KEY=votre_clé

# 4. Lancer le serveur
python app.py
API disponible sur : http://localhost:8001

🔧 Configuration
Variables d'environnement (.env)
ini
GROQ_API_KEY=votre_clé_api_groq
PORT=8001
ENVIRONMENT=development
Variable	Requise	Défaut	Description
GROQ_API_KEY	✅ OUI	-	Clé API pour le LLM Groq
PORT	❌ NON	8001	Port d'écoute
ENVIRONMENT	❌ NON	development	Environnement
📍 Endpoints
Santé
Méthode	Endpoint	Description
GET	/health	État détaillé des services
GET	/	Informations générales
Fonctionnalités principales
Méthode	Endpoint	Description
POST	/api/v1/autocomplete	Suggestions intelligentes
POST	/api/v1/reformulate	Reformulation d'observation
POST	/api/v1/extract_norme	Extraction de norme
POST	/api/v1/search	Recherche sémantique
Filtrage par thème
Méthode	Endpoint	Description
GET	/api/v1/themes/available	Liste des thèmes
POST	/api/v1/themes/suggest	Suggestions de thèmes
POST	/api/v1/themes/search	Recherche par thème
GET	/api/v1/themes/stats	Statistiques
📝 Exemples d'appels
Reformulation
bash
curl -X POST http://localhost:8001/api/v1/reformulate \
  -H "Content-Type: application/json" \
  -d '{
    "observation": "Les fil electrique son denudé",
    "theme": "câblage"
  }'
Réponse :

json
{
  "observation_corrigee": "Les fils électriques sont dénudés",
  "references_normatives": ["NFC 15-100 § 5.2.3"],
  "suggestions": ["Isoler les conducteurs", "Vérifier la section"]
}
Recherche sémantique
bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "section minimale des conducteurs",
    "top_k": 5
  }'
Suggestions de thèmes
bash
curl -X POST http://localhost:8001/api/v1/themes/suggest \
  -H "Content-Type: application/json" \
  -d '{"partial": "prot"}'
Réponse :

json
["protection", "protection différentielle"]
Vérification santé
bash
curl http://localhost:8001/health
Réponse :

json
{
  "status": "healthy",
  "engine_ready": true,
  "vector_store_ready": true,
  "groq_api_key": true
}
📊 Services internes
Service	Module	Rôle
VectorStore	core.vector_store	Index FAISS
SuggestionEngine	core.suggestion_engine	Moteur RAG
CorrectionPipeline	core.correction_pipeline	NLP
ThemeSearcher	core.theme_searcher	Filtrage
Groq LLM	core.groq_config	Inférence
📁 Structure
text
FastAPI_app/
├── app.py                 # Point d'entrée
├── api/
│   └── endpoints.py       # Routes
├── core/
│   ├── vector_store.py
│   ├── suggestion_engine.py
│   ├── correction_pipeline.py
│   ├── theme_searcher.py
│   └── groq_config.py
├── models/
│   └── schemas.py
├── utils/
├── tests/
└── .env
🧪 Tests
bash
# Tous les tests
pytest tests/

# Avec couverture
pytest --cov=. tests/
⚠️ Dépendances critiques
Élément	Requis	Description
GROQ_API_KEY	✅ OUI	Clé API Groq
data/index.faiss	✅ OUI	Index vectoriel
data/index.pkl	✅ OUI	Métadonnées
data/document_json/	✅ OUI	Corpus normes
🐛 Dépannage
ModuleNotFoundError: No module named 'core'
bash
cd FastAPI_app
python app.py
GROQ_API_KEY not found
bash
# Vérifier que .env existe
cat .env | grep GROQ_API_KEY
VectorStore not initialized
bash
# Vérifier que les données existent
ls ../data/index.faiss
📚 Documentation interactive
Swagger UI : http://localhost:8001/docs

ReDoc : http://localhost:8001/redoc

📝 Version
Version	Date	Changements
2.0.0	2024	Filtrage par thème, UTF-8 forcé
1.0.0	2023	Version initiale
👤 Auteur
Romuald AHOMAGNON - GitHub

📄 Licence
MIT

text

## ✅ Action finale

```powershell
# Créer le fichier
cd C:\USERS\ADMIN\DOWNLOADS\AI_INSPECTIONELECTRIQUE\mon_rag_api
notepad README.md

# Copier-coller le contenu ci-dessus
# Sauvegarder (Ctrl+S)