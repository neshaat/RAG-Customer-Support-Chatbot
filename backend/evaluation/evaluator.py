"""
Evaluation module — lightweight metrics for demo use.
Full RAGAS integration is provided but gated behind a flag to avoid
requiring an OpenAI key for the local demo.
"""
import time
from dataclasses import dataclass
from loguru import logger


@dataclass
class EvalMetrics:
    faithfulness: float       # 0-1: answer grounded in context?
    answer_relevancy: float   # 0-1: answer addresses the question?
    context_recall: float     # 0-1: relevant docs retrieved?
    custom_score: float       # composite
    latency_ms: float


# ── Heuristic (no-LLM) evaluator ─────────────────────────────────────────────

def _overlap_score(text_a: str, text_b: str) -> float:
    """Simple token-overlap Jaccard similarity."""
    a = set(text_a.lower().split())
    b = set(text_b.lower().split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def evaluate_response(
    question: str,
    answer: str,
    contexts: list[str],
    latency_ms: float = 0.0,
    use_ragas: bool = False,
) -> EvalMetrics:
    """
    Evaluate a single RAG response.

    Args:
        question:   Original user question.
        answer:     LLM-generated answer.
        contexts:   List of retrieved document chunks.
        latency_ms: End-to-end response time in ms.
        use_ragas:  If True, attempt full RAGAS evaluation (requires API key).
    """
    if use_ragas:
        return _ragas_evaluate(question, answer, contexts, latency_ms)
    return _heuristic_evaluate(question, answer, contexts, latency_ms)


def _heuristic_evaluate(question, answer, contexts, latency_ms) -> EvalMetrics:
    combined_context = " ".join(contexts)

    # Faithfulness: how much of the answer overlaps with retrieved context
    faithfulness = min(_overlap_score(answer, combined_context) * 3, 1.0)

    # Answer relevancy: how much the answer overlaps with the question
    answer_relevancy = min(_overlap_score(answer, question) * 4, 1.0)

    # Context recall: did any context chunk match the question?
    recall_scores = [_overlap_score(question, ctx) for ctx in contexts]
    context_recall = max(recall_scores) if recall_scores else 0.0

    custom_score = round(
        0.4 * faithfulness + 0.4 * answer_relevancy + 0.2 * context_recall, 3
    )

    return EvalMetrics(
        faithfulness=round(faithfulness, 3),
        answer_relevancy=round(answer_relevancy, 3),
        context_recall=round(context_recall, 3),
        custom_score=custom_score,
        latency_ms=round(latency_ms, 1),
    )


def _ragas_evaluate(question, answer, contexts, latency_ms) -> EvalMetrics:
    """Full RAGAS evaluation — requires datasets + ragas packages."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_recall

        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
            "ground_truth": [answer],   # self-reference for demo
        }
        ds = Dataset.from_dict(data)
        result = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_recall])
        scores = result.to_pandas().iloc[0]

        return EvalMetrics(
            faithfulness=round(float(scores.get("faithfulness", 0)), 3),
            answer_relevancy=round(float(scores.get("answer_relevancy", 0)), 3),
            context_recall=round(float(scores.get("context_recall", 0)), 3),
            custom_score=round(
                0.4 * float(scores.get("faithfulness", 0))
                + 0.4 * float(scores.get("answer_relevancy", 0))
                + 0.2 * float(scores.get("context_recall", 0)),
                3,
            ),
            latency_ms=round(latency_ms, 1),
        )
    except Exception as e:
        logger.warning(f"RAGAS evaluation failed, falling back to heuristic: {e}")
        return _heuristic_evaluate(question, answer, contexts, latency_ms)
