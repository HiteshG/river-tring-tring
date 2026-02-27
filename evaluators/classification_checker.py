"""
Classification Accuracy Checker (Layer 2 — Gemini LLM)
========================================================
Uses Gemini to verify if bot classifications match actual borrower intent.
Rubric: 1-3 scale (Correct → Wrong).
"""

from normalizer import NormalizedConversation
from evaluators.gemini_client import GeminiClient
from prompts.classification_prompt import CLASSIFICATION_PROMPT_TEMPLATE


class ClassificationChecker:
    """Check classification accuracy using Gemini LLM."""

    def __init__(self, api_key: str = None):
        self.client = GeminiClient(api_key=api_key)

    def check(self, conv: NormalizedConversation) -> list[dict]:
        """Run classification accuracy check and return violations."""
        prompt = self._build_prompt(conv)
        result = self.client.call(prompt, temperature=0.1)

        if result is None:
            return []

        return self._parse_findings(result)

    def _build_prompt(self, conv: NormalizedConversation) -> str:
        """Build the classification checking prompt."""
        cls_lines = []
        for turn in conv.borrower_turns:
            if turn.classification:
                cls_lines.append(
                    f"Turn {turn.turn_number}:\n"
                    f"  Borrower said: \"{turn.text}\"\n"
                    f"  Bot classified as: {turn.classification} "
                    f"(confidence: {turn.confidence})"
                )

        classifications_text = "\n\n".join(cls_lines) or "No classifications available."

        return CLASSIFICATION_PROMPT_TEMPLATE.format(
            classifications_text=classifications_text,
        )

    def _parse_findings(self, result: dict) -> list[dict]:
        """Convert LLM classification checks to violation records."""
        violations = []

        for eval_item in result.get("turn_evaluations", []):
            score = eval_item.get("accuracy_score", 1)
            if score <= 1:
                continue

            severity = (score - 1) / 2.0

            violations.append({
                "turn": eval_item.get("turn", 0),
                "rule": "Invariant I5 / Quality Q2 — Classification Accuracy",
                "severity": round(severity, 2),
                "category": "classification",
                "explanation": (
                    f"[Rubric {score}/3] Bot classified \"{eval_item.get('borrower_text', '')}\" "
                    f"as '{eval_item.get('bot_classification', '')}' but correct classification "
                    f"is likely '{eval_item.get('correct_classification', '')}'. "
                    f"{eval_item.get('reasoning', '')}"
                ),
            })

        misclass_rate = result.get("misclassification_rate", 0.0)
        if misclass_rate > 0.5:
            violations.append({
                "turn": 0,
                "rule": "Quality Q2 — Systematic Misclassification",
                "severity": min(1.0, misclass_rate),
                "category": "classification",
                "explanation": (
                    f"Overall misclassification rate: {misclass_rate:.0%}. "
                    f"More than half of borrower messages were incorrectly classified. "
                    f"{result.get('summary', '')}"
                ),
            })

        return violations
