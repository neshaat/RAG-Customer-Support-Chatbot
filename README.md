
<img width="1920" height="1249" alt="1774286733563" src="https://github.com/user-attachments/assets/4ddc4f78-b437-4fe2-bcfb-7899b978c65d" />


# 🤖 RAG Customer Support Chatbot

A local demo project combining LangChain + LLaMA, Multi-Intent NER, RAG pipeline, Kafka event streaming, SQLite DB, ngrok tunneling, and a polished frontend UI.

## Architecture

```
Frontend (HTML/CSS/JS)
       │  HTTP/REST
       ▼
Backend API (Flask)
   ├── RAG Pipeline (LangChain + LLaMA)
   │       ├── Intent Classifier (Multi-intent)
   │       ├── NER Extractor (spaCy)
   │       └── Vector Store (FAISS + HuggingFace Embeddings)
   ├── Guardrails (Input/Output validation)
   ├── Evaluator (RAGAS metrics)
   ├── Database (SQLite)
   └── Kafka Producer/Consumer (event logging)
       │  ngrok tunnel
       ▼
    Public URL (demo sharing)
```

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Pull LLaMA via Ollama (easiest local setup)
```bash
# Install Ollama: https://ollama.ai
ollama pull llama3.2
```

### 3. Start Kafka (Docker)
```bash
docker-compose up -d
```

### 4. Ingest knowledge base
```bash
python backend/rag/ingest.py
```

### 5. Start backend
```bash
python backend/app.py
```

### 6. (Optional) Expose via ngrok
```bash
ngrok http 5000
```

### 7. Open frontend
Open `frontend/index.html` in browser, or serve with:
```bash
python -m http.server 8080 --directory frontend
```

## Project Structure

```
rag-support-chatbot/
├── backend/
│   ├── app.py                  # Flask API server
│   ├── config.py               # Configuration
│   ├── rag/
│   │   ├── pipeline.py         # Main RAG chain
│   │   ├── ingest.py           # Document ingestion
│   │   └── knowledge_base/     # Sample docs (.txt/.pdf)
│   ├── kafka/
│   │   ├── producer.py         # Event producer
│   │   └── consumer.py         # Event consumer/logger
│   ├── db/
│   │   ├── models.py           # SQLAlchemy models
│   │   └── database.py         # DB connection
│   ├── guardrails/
│   │   └── validator.py        # Input/output safety checks
│   └── evaluation/
│       └── evaluator.py        # RAGAS + custom metrics
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/chat.js
├── docker-compose.yml          # Kafka + Zookeeper
├── requirements.txt
└── README.md
```
