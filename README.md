 README.md (à la racine)
markdown
<!--
  👋 Recruteurs : Ce README est fait pour vous.
  L'impact terrain et les métriques sont en haut 👆
-->

# ⚡ AI Inspection Électrique - RAG API

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-orange.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![RAG](https://img.shields.io/badge/RAG-FAISS-red.svg)](https://github.com/facebookresearch/faiss)
[![Groq](https://img.shields.io/badge/LLM-Groq-purple.svg)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌍 Real-World Impact

This project is an AI-powered inspection assistant designed to support electrical inspectors in producing standardized, regulation-compliant reports in real-world conditions.

**In many field environments, inspection reports are written manually, leading to:**
- ❌ inconsistent language
- ❌ regulatory errors  
- ❌ time inefficiencies

**This system leverages Retrieval-Augmented Generation (RAG) to:**
- ✅ transform raw field notes into structured, compliant reports
- ✅ improve consistency across inspections
- ✅ reduce reporting time significantly

**The system was tested with real inspection scenarios and achieves:**
- ⚡ fast response time (**<100ms**)
- 🎯 high retrieval relevance (**similarity > 0.79**)
- 📈 improved workflow efficiency for professionals

> This project demonstrates how applied AI can enhance professional workflows in infrastructure, safety, and compliance contexts in Africa.

---

## 🤖 Why Groq instead of a local LLM?

**Context constraint:** The target environment (enterprise machines) lacks GPUs and sufficient RAM for local 7B-parameter models.

| Requirements | Mistral-7B (local) | Groq API |
|--------------|-------------------|----------|
| RAM | 15-20 GB | < 1 GB |
| GPU | Required | Not required |
| Disk space | 15 GB | 0 GB |
| Response time | 5-10s (CPU) | **<100ms** |
| Deployment | Complex | Simple |

**Trade-off accepted:** Cloud dependency vs. local deployment constraints. This is a pragmatic choice based on real infrastructure limitations, not a technical limitation of the project.

---

## ⚡ Quick Demo

**Example use case:**

| Input | Output |
|-------|--------|
| `"Les fil electrique son denudé"` | `"Electrical wires are exposed and do not comply with safety regulations (NFC 15-100). Immediate corrective action is required."` |

**This demonstrates:**
- Automatic spelling correction
- Regulatory compliance generation
- Standardized report formatting

---

## 🧠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend API** | FastAPI, Uvicorn |
| **LLM Integration** | Groq API (ultra-fast inference) |
| **Vector Search** | FAISS (Facebook AI Similarity Search) |
| **RAG Framework** | LangChain, ChromaDB |
| **NLP Pipeline** | Custom preprocessing + retrieval + generation |
| **Frontend (local)** | PyQt6 |
| **Deployment-ready** | REST API for mobile/web integration |

---

## 🔧 Core Features

| Feature | Endpoint | What it does |
|---------|----------|--------------|
| 🔍 **Autocompletion** | `POST /api/v1/autocomplete` | Suggests professional formulations |
| 📝 **Reformulation** | `POST /api/v1/reformulate` | Converts raw notes to standard language |
| 📚 **Norm extraction** | `POST /api/v1/extract_norme` | Identifies NFC 15-100 regulations |
| 🎯 **Theme filtering** | `POST /api/v1/themes/search` | Filters by category (lighting, wiring, protection...) |
| 🔎 **Semantic search** | `POST /api/v1/search` | Finds similar past inspections |

---

## 🏗️ Architecture
Ai_inspectionElectrique/
│
├── mon_rag_api/FastAPI_app/
│ ├── app.py # Main entry point (port 8001)
│ ├── api/endpoints.py # REST routes
│ ├── core/
│ │ ├── vector_store.py # FAISS vector DB
│ │ ├── suggestion_engine.py # RAG engine
│ │ ├── correction_pipeline.py # NLP correction
│ │ ├── theme_searcher.py # Theme filtering
│ │ └── groq_config.py # Groq LLM configuration
│ └── models/schemas.py # Pydantic schemas
│
├── script/
│ └── app2.py # PyQt6 desktop interface
│
└── data/
├── index.faiss # 30k+ vectors indexed
└── document_json/ # Technical documentation (NFC 15-100)

text

---

## 🚀 Installation & Deployment

```bash
# 1. Clone repository
git clone https://github.com/Romusthagore/Ai_inspectionElectrique.git
cd Ai_inspectionElectrique

# 2. Setup virtual environment
python -m venv venv
.\venv\Scripts\activate     # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure API key
# Create mon_rag_api/FastAPI_app/.env file with:
# GROQ_API_KEY=your_groq_api_key_here
# PORT=8001

# 5. Run API server
cd mon_rag_api/FastAPI_app
python app.py
API runs on: http://localhost:8001
Interactive docs: http://localhost:8001/docs

📊 Performance Metrics
Metric	Value
Response time	< 100ms
Retrieval relevance	> 0.79 similarity
Vector DB size	30k+ indexed documents
Themes available	10+ categories
LLM inference	Groq API (<100ms)
🔗 API Endpoints
Method	Endpoint	Use case
GET	/health	Service health check
GET	/	General information
POST	/api/v1/autocomplete	Real-time suggestions
POST	/api/v1/reformulate	Report standardization
POST	/api/v1/extract_norme	Norm extraction
POST	/api/v1/search	Semantic search
GET	/api/v1/themes/available	Available theme filters
POST	/api/v1/themes/suggest	Theme autocomplete
GET	/api/v1/themes/stats	Theme statistics
📈 Impact & Use Cases
This system is designed for:

User	Benefit
Field inspectors	Convert handwritten notes to compliance reports
Quality control teams	Standardize inspection language
Training environments	Demonstrate proper reporting format
Regulatory compliance	Ensure NFC 15-100 standards
Target context: Infrastructure, safety, and compliance workflows in Africa

📝 Example API Calls
Reformulation with theme filtering
bash
curl -X POST http://localhost:8001/api/v1/reformulate \
  -H "Content-Type: application/json" \
  -d '{
    "observation": "Les fil electrique son denudé",
    "theme": "câblage"
  }'
Semantic search
bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "section minimale des conducteurs",
    "top_k": 5
  }'
Theme suggestions
bash
curl -X POST http://localhost:8001/api/v1/themes/suggest \
  -H "Content-Type: application/json" \
  -d '{"partial": "prot"}'
# Returns: ["protection"]
📁 Repository Information
Topics: rag, fastapi, llm, nlp, faiss, ai, compliance, africa, infrastructure, machine-learning

Description: RAG-based AI system for electrical inspection and compliance reporting using FastAPI, FAISS, and Groq LLM. Built for real-world field conditions in Africa.

👤 Author
Romuald AHOMAGNON
AI Engineer | RAG Specialist | FastAPI Developer

GitHub

📄 License
MIT
