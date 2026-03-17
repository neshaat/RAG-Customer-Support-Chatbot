"""
Guardrails: validate user inputs and LLM outputs before sending/returning.
"""
import re
from dataclasses import dataclass, field
from backend.config import MAX_INPUT_LENGTH, BLOCKED_KEYWORDS, MIN_RESPONSE_LEN


@dataclass
class GuardrailResult:
    passed: bool
    flags: list[str] = field(default_factory=list)
    sanitized_text: str = ""


# ── Input Guardrails ──────────────────────────────────────────────────────────

def validate_input(user_input: str) -> GuardrailResult:
    flags = []
    text = user_input.strip()

    # 1. Empty or too short
    if not text:
        return GuardrailResult(passed=False, flags=["empty_input"], sanitized_text=text)

    # 2. Too long
    if len(text) > MAX_INPUT_LENGTH:
        flags.append("input_too_long")
        text = text[:MAX_INPUT_LENGTH]

    # 3. Blocked keywords (prompt injection / misuse)
    lower = text.lower()
    triggered = [kw for kw in BLOCKED_KEYWORDS if kw in lower]
    if triggered:
        flags.append(f"blocked_keywords:{','.join(triggered)}")
        return GuardrailResult(passed=False, flags=flags, sanitized_text=text)

    # 4. Strip excessive whitespace / invisible chars
    text = re.sub(r"\s+", " ", text).strip()

    return GuardrailResult(passed=True, flags=flags, sanitized_text=text)


# ── Output Guardrails ─────────────────────────────────────────────────────────

def validate_output(response: str) -> GuardrailResult:
    flags = []
    text = response.strip()

    # 1. Too short (likely a failure)
    if len(text) < MIN_RESPONSE_LEN:
        flags.append("response_too_short")
        return GuardrailResult(passed=False, flags=flags, sanitized_text=text)

    # 2. Check for leaked system-prompt artefacts
    suspicious_patterns = [
        r"<\|system\|>", r"<\|user\|>", r"<\|assistant\|>",   # chat templates
        r"ignore (all )?previous instructions",
        r"you are (now )?DAN",
    ]
    for pat in suspicious_patterns:
        if re.search(pat, text, re.IGNORECASE):
            flags.append(f"suspicious_pattern:{pat}")
            return GuardrailResult(passed=False, flags=flags, sanitized_text=text)

    # 3. Basic PII scrub — redact obvious email / phone
    text = re.sub(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", "[EMAIL REDACTED]", text)
    text = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE REDACTED]", text)

    if text != response.strip():
        flags.append("pii_redacted")

    return GuardrailResult(passed=True, flags=flags, sanitized_text=text)
