"""
Flask API — main entry point.
Run:  python backend/app.py
"""
import uuid
import time
import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from loguru import logger

from backend.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, KAFKA_TOPIC_QUERIES, KAFKA_TOPIC_RESPONSES, KAFKA_TOPIC_EVALS
from backend.db.database import init_db, SessionLocal
from backend.db.models import Message, Conversation, EvaluationResult
from backend.guardrails.validator import validate_input, validate_output
from backend.kafka.producer import publish_event
from backend.kafka.consumer import start_background_consumer
from backend.rag.pipeline import run_rag
from backend.evaluation.evaluator import evaluate_response

app = Flask(__name__)
CORS(app)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/chat")
def chat():
    body       = request.get_json(silent=True) or {}
    user_input = body.get("message", "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())

    # ── 1. Input guardrail
    guard_in = validate_input(user_input)
    if not guard_in.passed:
        return jsonify({
            "session_id": session_id,
            "answer": "I'm sorry, I couldn't process that message. Please rephrase your question.",
            "guardrail_flags": guard_in.flags,
            "intents": [],
            "entities": [],
            "sources": [],
            "metrics": None,
        }), 400

    # ── 2. Publish query event
    publish_event(KAFKA_TOPIC_QUERIES, {
        "session_id": session_id,
        "message": guard_in.sanitized_text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # ── 3. RAG pipeline
    try:
        t0  = time.time()
        rag = run_rag(guard_in.sanitized_text)
        latency_ms = (time.time() - t0) * 1000
    except Exception as e:
        logger.error(f"RAG error: {e}")
        return jsonify({"answer": "Service temporarily unavailable.", "error": str(e)}), 503

    # ── 4. Output guardrail
    guard_out = validate_output(rag["answer"])
    final_answer = guard_out.sanitized_text if guard_out.passed else (
        "I encountered an issue generating a response. Please try again."
    )

    # ── 5. Evaluate
    metrics = evaluate_response(
        question=guard_in.sanitized_text,
        answer=final_answer,
        contexts=rag["contexts"],
        latency_ms=rag["latency_ms"],
    )

    all_flags = guard_in.flags + guard_out.flags

    # ── 6. Persist to DB
    db = SessionLocal()
    try:
        msg = Message(
            session_id=session_id,
            role="assistant",
            content=final_answer,
            intents=rag["intents"],
            entities=rag["entities"],
            sources=rag["sources"],
            guardrail_flags=all_flags,
        )
        db.add(msg)
        db.flush()

        db.add(EvaluationResult(
            message_id=msg.id,
            faithfulness=metrics.faithfulness,
            answer_relevancy=metrics.answer_relevancy,
            context_recall=metrics.context_recall,
            custom_score=metrics.custom_score,
        ))
        db.commit()
    except Exception as e:
        logger.error(f"DB error: {e}")
        db.rollback()
    finally:
        db.close()

    # ── 7. Publish response + eval events
    publish_event(KAFKA_TOPIC_RESPONSES, {
        "session_id": session_id,
        "intents": rag["intents"],
        "latency_ms": rag["latency_ms"],
        "timestamp": datetime.utcnow().isoformat(),
    })
    publish_event(KAFKA_TOPIC_EVALS, {
        "session_id": session_id,
        "faithfulness": metrics.faithfulness,
        "answer_relevancy": metrics.answer_relevancy,
        "custom_score": metrics.custom_score,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return jsonify({
        "session_id":      session_id,
        "answer":          final_answer,
        "intents":         rag["intents"],
        "entities":        rag["entities"],
        "sources":         rag["sources"],
        "guardrail_flags": all_flags,
        "metrics": {
            "faithfulness":     metrics.faithfulness,
            "answer_relevancy": metrics.answer_relevancy,
            "context_recall":   metrics.context_recall,
            "custom_score":     metrics.custom_score,
            "latency_ms":       metrics.latency_ms,
        },
    })


# ── History ───────────────────────────────────────────────────────────────────

@app.get("/history/<session_id>")
def history(session_id: str):
    db = SessionLocal()
    try:
        messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()
        return jsonify([{
            "role":       m.role,
            "content":    m.content,
            "intents":    m.intents,
            "entities":   m.entities,
            "created_at": m.created_at.isoformat(),
        } for m in messages])
    finally:
        db.close()


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    start_background_consumer()

    # Optional ngrok tunnel (set NGROK_AUTH_TOKEN in .env)
    if os.getenv("NGROK_AUTH_TOKEN"):
        try:
            from backend.ngrok_tunnel import start_tunnel
            start_tunnel(FLASK_PORT)
        except ImportError:
            logger.warning("pyngrok not installed — skipping ngrok. Run: pip install pyngrok")

    logger.info(f"Starting server → http://{FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
