"""
Quality Evaluator (Layer 2 — Gemini LLM)
==========================================
Uses Gemini to evaluate message quality per spec Section 10.
Rubric: 1-3 scale (Good → Failing).
"""

from normalizer import NormalizedConversation
from evaluators.gemini_client import GeminiClient
from prompts.quality_prompt import QUALITY_PROMPT_TEMPLATE


class QualityEvaluator:
    """Evaluate message quality using Gemini LLM."""

    def __init__(self, api_key: str = None):
        self.client = GeminiClient(api_key=api_key)

    def check(self, conv: NormalizedConversation) -> list[dict]:
        """Run quality evaluation and return violations."""
        prompt = self._build_prompt(conv)
        result = self.client.call(prompt, temperature=0.1)

        if result is None:
            return []

        return self._parse_findings(result)

    def _build_prompt(self, conv: NormalizedConversation) -> str:
        """Build the quality evaluation prompt."""
        meta = conv.metadata

        conv_lines = []
        for turn in conv.turns:
            cls_info = ""
            if turn.classification:
                cls_info = f" [classified: {turn.classification}/{turn.confidence}]"
            conv_lines.append(
                f"Turn {turn.turn_number} ({turn.role}): {turn.text}{cls_info}"
            )
        conversation_text = "\n".join(conv_lines)

        return QUALITY_PROMPT_TEMPLATE.format(
            total_turns=meta.get("total_turns", len(conv.turns)),
            final_state=conv.final_state or "unknown",
            language=meta.get("language", "unknown"),
            conversation_text=conversation_text,
        )

    def _parse_findings(self, result: dict) -> list[dict]:
        """Convert LLM quality assessment to violation records."""
        violations = []
        dimensions = result.get("dimensions", {})

        dimension_rules = {
            "Q1_efficient_progress": "Quality Q1 — Efficient Progress",
            "Q2_classification_impact": "Quality Q2 — Classification Impact on Flow",
            "Q3_appropriate_tone": "Quality Q3 — Appropriate Tone",
            "Q4_context_retention": "Quality Q4 — Context Retention",
            "Q5_no_repetition": "Quality Q5 — No Repetition",
        }

        for dim_key, rule_name in dimension_rules.items():
            dim = dimensions.get(dim_key, {})
            score = dim.get("score", 1)

            if score <= 1:
                continue

            severity = (score - 1) / 2.0
            problem_turns = dim.get("problem_turns", [])
            turn_ref = problem_turns[0] if problem_turns else 0

            violations.append({
                "turn": turn_ref,
                "rule": rule_name,
                "severity": round(severity, 2),
                "category": "quality",
                "explanation": (
                    f"[Rubric {score}/3] {dim.get('reasoning', '')} "
                    f"Turns affected: {problem_turns}"
                ),
            })

        return violations
