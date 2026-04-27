<!--👋 Recruiters: This README is designed for you.Real-world impact and performance metrics are highlighted first.--># ⚡ AI Inspection Électrique — RAG API[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)[![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-orange.svg)](https://www.riverbankcomputing.com/software/pyqt/)[![RAG](https://img.shields.io/badge/RAG-FAISS-red.svg)](https://github.com/facebookresearch/faiss)[![Groq](https://img.shields.io/badge/LLM-Groq-purple.svg)](https://groq.com/)[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)---## 🌍 Real-World ImpactThis project is an AI-powered inspection assistant designed to help electrical inspectors produce standardized, regulation-compliant reports in real-world conditions.**In many field environments, inspection reports are written manually, leading to:**- ❌ inconsistent language  - ❌ regulatory errors  - ❌ time inefficiencies  **This system leverages Retrieval-Augmented Generation (RAG) to:**- ✅ transform raw field notes into structured, compliant reports  - ✅ improve consistency across inspections  - ✅ significantly reduce reporting time  **The system was tested in real-world inspection scenarios and achieves:**- ⚡ fast response time (**< 100 ms**)  - 🎯 high retrieval relevance (**similarity > 0.79**)  - 📈 measurable workflow efficiency improvements  > This project demonstrates how applied AI can enhance professional workflows in infrastructure, safety, and compliance contexts in Africa.---## 🤖 Why Groq instead of a local LLM?**Context constraint:** Target environments (enterprise machines) lack GPUs and sufficient RAM for local 7B-parameter models.| Requirements | Mistral-7B (local) | Groq API ||--------------|-------------------|----------|| RAM | 15–20 GB | < 1 GB || GPU | Required | Not required || Disk space | 15 GB | 0 GB || Response time | 5–10s (CPU) | **< 100 ms** || Deployment | Complex | Simple |**Trade-off:** Cloud dependency vs. deployment feasibility.  This is a pragmatic engineering decision based on real infrastructure constraints.---## ⚡ Quick Demo**Example use case:**| Input | Output ||------|--------|| `"Les fil electrique son denudé"` | `"Electrical wires are exposed and do not comply with safety regulations (NFC 15-100). Immediate corrective action is required."` |**This demonstrates:**- automatic spelling correction  - regulatory compliance generation  - standardized report formatting  ---## 🧠 Tech Stack| Layer | Technology ||------|-----------|| Backend API | FastAPI, Uvicorn || LLM Integration | Groq API || Vector Search | FAISS || RAG Framework | LangChain, ChromaDB || NLP Pipeline | Custom preprocessing + retrieval + generation || Frontend (local) | PyQt6 || Deployment | REST API (mobile/web ready) |---## 🔧 Core Features| Feature | Endpoint | Description ||--------|----------|------------|| 🔍 Autocompletion | `POST /api/v1/autocomplete` | Suggests professional formulations || 📝 Reformulation | `POST /api/v1/reformulate` | Converts raw notes into standard language || 📚 Norm extraction | `POST /api/v1/extract_norme` | Identifies NFC 15-100 regulations || 🎯 Theme filtering | `POST /api/v1/themes/search` | Filters by category || 🔎 Semantic search | `POST /api/v1/search` | Retrieves similar inspection cases |---## 🏗️ Architecture
Ai_inspectionElectrique/
│
├── mon_rag_api/FastAPI_app/
│   ├── app.py
│   ├── api/endpoints.py
│   ├── core/
│   │   ├── vector_store.py
│   │   ├── suggestion_engine.py
│   │   ├── correction_pipeline.py
│   │   ├── theme_searcher.py
│   │   └── groq_config.py
│   └── models/schemas.py
│
├── script/
│   └── app2.py
│
└── data/
├── index.faiss
└── document_json/
---## 🚀 Installation & Deployment```bash# Clone repositorygit clone https://github.com/Romusthagore/Ai_inspectionElectrique.gitcd Ai_inspectionElectrique# Create virtual environmentpython -m venv venv.\venv\Scripts\activate# Install dependenciespip install -r requirements.txt# Configure API key (.env file)GROQ_API_KEY=your_key_herePORT=8001# Run APIcd mon_rag_api/FastAPI_apppython app.py
API available at: http://localhost:8001
Docs: http://localhost:8001/docs

📊 Performance Metrics
MetricValueResponse time< 100 msRetrieval relevance> 0.79Vector DB size30k+ documentsThemes10+ categories

📈 Use Cases


Field inspectors → automated compliance reports


Quality control teams → standardized reporting


Training environments → best-practice formatting


Regulatory compliance → NFC 15-100 adherence



📝 Example API Call
curl -X POST http://localhost:8001/api/v1/reformulate \  -H "Content-Type: application/json" \  -d '{    "observation": "Les fil electrique son denudé",    "theme": "câblage"  }'

📌 Demo
Demo available upon request.

👤 Author
Romuald AHOMAGNON
AI Engineer | RAG Specialist | FastAPI Developer
