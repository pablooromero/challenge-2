import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

GuardrailCategory = Literal[
    "prompt_injection",
    "sensitive_request",
    "arbitrary_execution",
    "needs_clarification",
]


@dataclass(frozen=True)
class GuardrailRule:
    category: GuardrailCategory
    pattern_name: str
    reason: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class GuardrailMatch:
    category: GuardrailCategory
    pattern_name: str
    reason: str
    matched_text: str

    def as_metadata(self) -> dict[str, str]:
        return {
            "guardrail_category": self.category,
            "guardrail_pattern": self.pattern_name,
            "guardrail_reason": self.reason,
            "guardrail_match": self.matched_text[:120],
        }


def normalize_guardrail_text(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(without_accents.lower().split())


RESTRICTED_RULES: tuple[GuardrailRule, ...] = (
    GuardrailRule(
        category="prompt_injection",
        pattern_name="ignore_instructions",
        reason="prompt_injection_detected",
        pattern=re.compile(r"\b(ignora|olvida)\s+(tus|las)\s+instrucciones\b"),
    ),
    GuardrailRule(
        category="prompt_injection",
        pattern_name="system_prompt_request",
        reason="prompt_injection_detected",
        pattern=re.compile(
            r"\b(system prompt|prompt del sistema|developer message|mensaje de sistema|mensaje del desarrollador)\b"
        ),
    ),
    GuardrailRule(
        category="sensitive_request",
        pattern_name="secret_request",
        reason="sensitive_request_blocked",
        pattern=re.compile(
            r"\b(api key|clave api|secret key|credenciales|password|contrasena|\.env|mysql password|token)\b"
        ),
    ),
    GuardrailRule(
        category="arbitrary_execution",
        pattern_name="sql_execution_request",
        reason="arbitrary_execution_blocked",
        pattern=re.compile(r"\b(ejecuta|genera)\s+sql\b"),
    ),
    GuardrailRule(
        category="arbitrary_execution",
        pattern_name="destructive_sql",
        reason="arbitrary_execution_blocked",
        pattern=re.compile(r"\b(drop table|delete from|truncate table)\b"),
    ),
    GuardrailRule(
        category="arbitrary_execution",
        pattern_name="code_execution_request",
        reason="arbitrary_execution_blocked",
        pattern=re.compile(r"\b(rm\s+-rf|ejecuta codigo|corre codigo)\b"),
    ),
)

AMBIGUOUS_RULES: tuple[GuardrailRule, ...] = (
    GuardrailRule(
        category="needs_clarification",
        pattern_name="underspecified_followup",
        reason="ambiguous_request_requires_metric_or_dimension",
        pattern=re.compile(
            r"\b(como viene|como vamos|que paso|y eso|detallalo|explicame mejor|mostrame mas|amplia eso)\b"
        ),
    ),
)

DOMAIN_HINT_PATTERN = re.compile(
    r"\b(lead|venta|ingres|revenue|costo|gasto|inversion|clic|click|impres|ctr|cpl|cpa|roas|conversion|mes|canal|google ads|meta ads|vehiculo|modelo|proximo mes|forecast)\b"
)


def _match_first_rule(question: str, rules: tuple[GuardrailRule, ...]) -> GuardrailMatch | None:
    normalized = normalize_guardrail_text(question)
    for rule in rules:
        match = rule.pattern.search(normalized)
        if match:
            return GuardrailMatch(
                category=rule.category,
                pattern_name=rule.pattern_name,
                reason=rule.reason,
                matched_text=match.group(0),
            )
    return None


def detect_restricted_request(question: str) -> GuardrailMatch | None:
    return _match_first_rule(question, RESTRICTED_RULES)


def detect_ambiguous_question(question: str) -> GuardrailMatch | None:
    matched_rule = _match_first_rule(question, AMBIGUOUS_RULES)
    if matched_rule is not None:
        return matched_rule

    normalized = normalize_guardrail_text(question)
    if len(normalized.split()) <= 3 and DOMAIN_HINT_PATTERN.search(normalized) is None:
        return GuardrailMatch(
            category="needs_clarification",
            pattern_name="short_query_without_domain_context",
            reason="ambiguous_request_requires_metric_or_dimension",
            matched_text=normalized[:120],
        )

    return None
