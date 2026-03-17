from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Conversation(Base):
    """Stores each chat session."""
    __tablename__ = "conversations"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    """Stores individual messages within a conversation."""
    __tablename__ = "messages"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    session_id      = Column(String(64), nullable=False, index=True)
    role            = Column(String(16), nullable=False)   # "user" | "assistant"
    content         = Column(Text, nullable=False)
    intents         = Column(JSON)                          # detected intents list
    entities        = Column(JSON)                          # NER results
    sources         = Column(JSON)                          # RAG source docs
    guardrail_flags = Column(JSON)                          # any triggered flags
    created_at      = Column(DateTime, default=datetime.utcnow)


class EvaluationResult(Base):
    """Stores per-response evaluation metrics."""
    __tablename__ = "evaluation_results"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    message_id      = Column(Integer, nullable=False)
    faithfulness    = Column(Float)
    answer_relevancy = Column(Float)
    context_recall  = Column(Float)
    custom_score    = Column(Float)
    evaluated_at    = Column(DateTime, default=datetime.utcnow)
