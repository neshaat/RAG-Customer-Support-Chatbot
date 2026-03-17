"""
Core RAG pipeline: Multi-Intent classification, NER, retrieval, and generation.
"""
import time
import spacy
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from loguru import logger

from backend.config import (
    OLLAMA_BASE_URL, LLM_MODEL, EMBEDDING_MODEL,
    VECTOR_STORE_PATH, TOP_K_DOCS, MAX_RESPONSE_TOKENS,
)

# ── Intent definitions ────────────────────────────────────────────────────────

INTENT_KEYWORDS: dict[str, list[str]] = {
    "order_status":       ["order", "shipment", "shipping", "track", "delivery", "where is my"],
    "return_refund":      ["return", "refund", "money back", "exchange", "send back"],
    "product_inquiry":    ["product", "item", "spec", "feature", "price", "cost", "how much"],
    "account_issue":      ["account", "login", "password", "sign in", "access", "profile"],
    "complaint":          ["complaint", "angry", "frustrated", "unhappy", "terrible", "worst"],
    "general_support":    ["help", "support", "issue", "problem", "broken", "not working"],
}

# ── Lazy-loaded globals ───────────────────────────────────────────────────────

_nlp    = None
_llm    = None
_store  = None
_chain  = None

SYSTEM_PROMPT = """You are a helpful, professional customer support assistant.
Answer the customer's question using ONLY the provided context.
If the context doesn't contain the answer, say "I don't have information about that, please contact support@company.com."
Be concise, friendly, and accurate.

Context:
{context}

Question: {question}
Answer:"""


def _load_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            _nlp = None
    return _nlp


def _load_llm():
    global _llm
    if _llm is None:
        _llm = OllamaLLM(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            num_predict=MAX_RESPONSE_TOKENS,
            temperature=0.3,
        )
        logger.info(f"LLM loaded: {LLM_MODEL}")
    return _llm


def _load_vector_store():
    global _store
    if _store is None:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        try:
            _store = FAISS.load_local(
                VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True
            )
            logger.info("Vector store loaded.")
        except Exception as e:
            logger.error(f"Could not load vector store: {e}. Run backend/rag/ingest.py first.")
            raise
    return _store


def _build_chain():
    global _chain
    if _chain is None:
        llm   = _load_llm()
        store = _load_vector_store()
        prompt = PromptTemplate(
            template=SYSTEM_PROMPT,
            input_variables=["context", "question"],
        )
        _chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=store.as_retriever(search_kwargs={"k": TOP_K_DOCS}),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True,
        )
    return _chain


# ── Public API ────────────────────────────────────────────────────────────────

def classify_intents(text: str) -> list[str]:
    """Multi-intent classifier based on keyword matching."""
    lower = text.lower()
    matched = [intent for intent, kws in INTENT_KEYWORDS.items() if any(kw in lower for kw in kws)]
    return matched if matched else ["general_support"]


def extract_entities(text: str) -> list[dict]:
    """Named Entity Recognition using spaCy."""
    nlp = _load_nlp()
    if nlp is None:
        return []
    doc = nlp(text)
    return [{"text": ent.text, "label": ent.label_, "description": spacy.explain(ent.label_)} for ent in doc.ents]


def run_rag(question: str) -> dict:
    """
    Full pipeline: intents → NER → retrieval → generation.
    Returns dict with answer, sources, intents, entities, latency_ms.
    """
    t0 = time.time()

    intents  = classify_intents(question)
    entities = extract_entities(question)

    chain = _build_chain()
    result = chain.invoke({"query": question})

    latency_ms = (time.time() - t0) * 1000
    answer     = result.get("result", "").strip()
    source_docs = result.get("source_documents", [])
    sources     = [
        {"content": doc.page_content[:200], "source": doc.metadata.get("source", "unknown")}
        for doc in source_docs
    ]
    contexts = [doc.page_content for doc in source_docs]

    return {
        "answer":     answer,
        "intents":    intents,
        "entities":   entities,
        "sources":    sources,
        "contexts":   contexts,
        "latency_ms": round(latency_ms, 1),
    }
