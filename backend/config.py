import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL       = os.getenv("LLM_MODEL", "llama3.2")          # or llama3, llama2
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── RAG ──────────────────────────────────────────────
VECTOR_STORE_PATH   = os.getenv("VECTOR_STORE_PATH", "backend/rag/vector_store")
KNOWLEDGE_BASE_PATH = os.getenv("KNOWLEDGE_BASE_PATH", "backend/rag/knowledge_base")
CHUNK_SIZE          = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP       = int(os.getenv("CHUNK_OVERLAP", 50))
TOP_K_DOCS          = int(os.getenv("TOP_K_DOCS", 4))

# ── Database ─────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///backend/db/chatbot.db")

# ── Kafka ─────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_QUERIES     = "chatbot.queries"
KAFKA_TOPIC_RESPONSES   = "chatbot.responses"
KAFKA_TOPIC_EVALS       = "chatbot.evaluations"

# ── Guardrails ────────────────────────────────────────
MAX_INPUT_LENGTH   = 1000
BLOCKED_KEYWORDS   = ["hack", "exploit", "jailbreak", "ignore previous instructions"]
MIN_RESPONSE_LEN   = 10
MAX_RESPONSE_TOKENS = 512

# ── Server ────────────────────────────────────────────
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
