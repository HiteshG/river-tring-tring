"""
Compliance Evaluator (Layer 2 — Gemini LLM)
=============================================
Uses Gemini to evaluate compliance with spec Section 8.
Rubric: 1-5 scale (Clean → Critical).
"""

from normalizer import NormalizedConversation
from evaluators.gemini_client import GeminiClient
from prompts.compliance_prompt import COMPLIANCE_PROMPT_TEMPLATE


class ComplianceEvaluator:
    """Evaluate compliance requirements using Gemini LLM."""

    def __init__(self, api_key: str = None):
        self.client = GeminiClient(api_key=api_key)

    def check(self, conv: NormalizedConversation) -> list[dict]:
        """Run compliance evaluation and return violations."""
        prompt = self._build_prompt(conv)
        result = self.client.call(prompt, temperature=0.1)

        if result is None:
            return []

        return self._parse_findings(result, conv)

    def _build_prompt(self, conv: NormalizedConversation) -> str:
        """Build the compliance evaluation prompt."""
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

        tr_lines = []
        for tr in conv.state_transitions:
            tr_lines.append(
                f"Turn {tr['turn']}: {tr['from_state']} → {tr['to_state']} ({tr['reason']})"
            )
        transitions_text = "\n".join(tr_lines) or "No transitions recorded."

        return COMPLIANCE_PROMPT_TEMPLATE.format(
            language=meta.get("language", "unknown"),
            zone=meta.get("zone", "unknown"),
            dpd=meta.get("dpd", "unknown"),
            conversation_text=conversation_text,
            transitions_text=transitions_text,
        )

    def _parse_findings(self, result: dict, conv: NormalizedConversation) -> list[dict]:
        """Convert LLM findings to violation records."""
        violations = []

        for finding in result.get("findings", []):
            rubric_score = finding.get("rubric_score", 1)
            if rubric_score <= 1:
                continue

            severity = (rubric_score - 1) / 4.0

            violations.append({
                "turn": finding.get("turn", 0),
                "rule": f"Section 8 — Compliance: {finding.get('dimension', 'unknown')}",
                "severity": round(severity, 2),
                "category": "compliance",
                "explanation": (
                    f"[Rubric {rubric_score}/5] {finding.get('reasoning', '')} "
                    f"Expected: {finding.get('expected_behavior', 'N/A')}"
                ),
            })

        return violations
