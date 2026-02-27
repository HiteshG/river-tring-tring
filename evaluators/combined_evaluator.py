"""
Combined LLM Evaluator (Layer 2 — Single Gemini Call)
======================================================
Merges compliance, quality, and classification evaluation into
ONE Gemini API call per conversation. 3x faster than 3 separate calls.
"""

from normalizer import NormalizedConversation
from evaluators.gemini_client import GeminiClient
from prompts.combined_prompt import COMBINED_PROMPT_TEMPLATE


class CombinedLLMEvaluator:
    """Single-call LLM evaluator combining compliance + quality + classification."""

    def __init__(self, api_key: str = None):
        self.client = GeminiClient(api_key=api_key)

    def check(self, conv: NormalizedConversation) -> list[dict]:
        """Run all three evaluations in one LLM call."""
        prompt = self._build_prompt(conv)
        result = self.client.call(prompt, temperature=0.1)

        if result is None:
            return []

        violations = []
        violations.extend(self._parse_compliance(result))
        violations.extend(self._parse_quality(result))
        violations.extend(self._parse_classification(result))
        return violations

    def _build_prompt(self, conv: NormalizedConversation) -> str:
        meta = conv.metadata

        conv_lines = []
        for turn in conv.turns:
            cls = f" [{turn.classification}/{turn.confidence}]" if turn.classification else ""
            conv_lines.append(f"T{turn.turn_number} ({turn.role}): {turn.text}{cls}")
        conversation_text = "\n".join(conv_lines)

        cls_lines = []
        for turn in conv.borrower_turns:
            if turn.classification:
                cls_lines.append(
                    f"T{turn.turn_number}: \"{turn.text}\" → {turn.classification} ({turn.confidence})"
                )
        classifications_text = "\n".join(cls_lines) or "None"

        tr_lines = [
            f"T{t['turn']}: {t['from_state']}→{t['to_state']} ({t['reason']})"
            for t in conv.state_transitions
        ]
        transitions_text = "\n".join(tr_lines) or "None"

        return COMBINED_PROMPT_TEMPLATE.format(
            language=meta.get("language", "unknown"),
            zone=meta.get("zone", "unknown"),
            dpd=meta.get("dpd", "unknown"),
            total_turns=meta.get("total_turns", len(conv.turns)),
            final_state=conv.final_state or "unknown",
            conversation_text=conversation_text,
            classifications_text=classifications_text,
            transitions_text=transitions_text,
        )

    def _parse_compliance(self, result: dict) -> list[dict]:
        violations = []
        compliance = result.get("compliance", {})
        for f in compliance.get("findings", []):
            score = f.get("rubric_score", 1)
            if score <= 1:
                continue
            severity = (score - 1) / 4.0
            violations.append({
                "turn": f.get("turn", 0),
                "rule": f"Section 8 — Compliance: {f.get('dimension', 'unknown')}",
                "severity": round(severity, 2),
                "category": "compliance",
                "explanation": f"[Rubric {score}/5] {f.get('reasoning', '')}",
            })
        return violations

    def _parse_quality(self, result: dict) -> list[dict]:
        violations = []
        quality = result.get("quality", {})
        dim_rules = {
            "Q1_efficient_progress": "Quality Q1 — Efficient Progress",
            "Q2_classification_impact": "Quality Q2 — Classification Impact on Flow",
            "Q3_appropriate_tone": "Quality Q3 — Appropriate Tone",
            "Q4_context_retention": "Quality Q4 — Context Retention",
            "Q5_no_repetition": "Quality Q5 — No Repetition",
        }
        for key, rule in dim_rules.items():
            dim = quality.get(key, {})
            score = dim.get("score", 1)
            if score <= 1:
                continue
            severity = (score - 1) / 2.0
            turns = dim.get("turns", [])
            violations.append({
                "turn": turns[0] if turns else 0,
                "rule": rule,
                "severity": round(severity, 2),
                "category": "quality",
                "explanation": f"[Rubric {score}/3] {dim.get('reasoning', '')} Turns: {turns}",
            })
        return violations

    def _parse_classification(self, result: dict) -> list[dict]:
        violations = []
        cls = result.get("classification", {})
        for err in cls.get("errors", []):
            score = err.get("score", 1)
            if score <= 1:
                continue
            severity = (score - 1) / 2.0
            violations.append({
                "turn": err.get("turn", 0),
                "rule": "Invariant I5 / Quality Q2 — Classification Accuracy",
                "severity": round(severity, 2),
                "category": "classification",
                "explanation": (
                    f"[Rubric {score}/3] Bot labeled '{err.get('bot_label', '')}' "
                    f"→ should be '{err.get('correct_label', '')}'. "
                    f"{err.get('reasoning', '')}"
                ),
            })

        misclass_rate = cls.get("misclassification_rate", 0)
        if misclass_rate > 0.5:
            violations.append({
                "turn": 0,
                "rule": "Quality Q2 — Systematic Misclassification",
                "severity": min(1.0, misclass_rate),
                "category": "classification",
                "explanation": f"Misclassification rate: {misclass_rate:.0%}. Over half of messages incorrectly classified.",
            })
        return violations
