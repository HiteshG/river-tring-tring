"""
Riverline Evals Take-Home Assignment
=====================================
Hybrid Evaluator: Deterministic Core + Gemini LLM Judgment

Architecture:
  Layer 1 (Deterministic): State transitions, timing, amounts
  Layer 2 (Gemini LLM):    Compliance, quality, classification accuracy
  Conversation-Level:      Loop detection, risk synthesis
  Aggregator:             Combines all modules → quality_score, risk_score, violations

Run locally:
    python eval_takehome.py
"""

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

from normalizer import EventNormalizer
from validators.state_validator import StateTransitionValidator
from validators.timing_validator import TimingValidator
from validators.amount_validator import AmountValidator
from evaluators.combined_evaluator import CombinedLLMEvaluator
from evaluators.compliance_evaluator import ComplianceEvaluator
from evaluators.quality_evaluator import QualityEvaluator
from evaluators.classification_checker import ClassificationChecker


# ── Category weights for quality score deductions ──────────────────────
# These weights control how much each violation category affects the
# overall quality score. Sum does not need to equal 1.0 — they are
# multiplied by severity and subtracted from 1.0.
CATEGORY_WEIGHTS = {
    "state_integrity": 0.25,
    "compliance": 0.30,
    "timing": 0.10,
    "amounts": 0.15,
    "quality": 0.10,
    "classification": 0.10,
}

# ── Severity thresholds for risk score ─────────────────────────────────
CRITICAL_SEVERITY = 0.9
HIGH_SEVERITY = 0.7
MODERATE_SEVERITY = 0.4

# ── Loop detection thresholds ──────────────────────────────────────────
LOOP_SIMILARITY_THRESHOLD = 0.85
LOOP_MIN_REPEATS = 3

# ── Valid LLM modes ───────────────────────────────────────────────────
LLM_MODES = ("combined", "separate")


class AgentEvaluator:
    """
    Evaluate WhatsApp debt collection conversations against the agent specification.

    Two-layer hybrid approach:
      - Layer 1: Deterministic checks (hard rules, exact reasoning)
      - Layer 2: Gemini LLM evaluation (soft judgment, rubric-based)

    Args:
        mode: 'combined' (1 LLM call, faster) or 'separate' (3 LLM calls, more thorough)
    """

    def __init__(self, mode: str = "combined"):
        """Initialize all evaluation modules.

        Args:
            mode: 'combined' — single LLM call (3x faster, recommended for batch)
                  'separate' — 3 separate LLM calls (more thorough compliance analysis)
        """
        if mode not in LLM_MODES:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {LLM_MODES}")

        self.mode = mode

        # Layer 1: Deterministic validators
        self.normalizer = EventNormalizer()
        self.state_validator = StateTransitionValidator()
        self.timing_validator = TimingValidator()
        self.amount_validator = AmountValidator()

        # Layer 2: Gemini LLM evaluator(s)
        if mode == "combined":
            self.llm_evaluator = CombinedLLMEvaluator()
        else:
            self.compliance_evaluator = ComplianceEvaluator()
            self.quality_evaluator = QualityEvaluator()
            self.classification_checker = ClassificationChecker()

    def evaluate(self, conversation: dict) -> dict:
        """
        Evaluate a single conversation.

        Args:
            conversation: dict with keys:
                - conversation_id: str
                - messages: list of {role, text, timestamp, turn}
                - bot_classifications: list of {turn, input_text, classification, confidence}
                - state_transitions: list of {turn, from_state, to_state, reason}
                - function_calls: list of {turn, function, params}
                - metadata: {language, zone, dpd, pos, tos, total_turns, ...}

        Returns:
            dict with keys:
                - quality_score: float 0-1 (higher = better conversation)
                - risk_score: float 0-1 (higher = more likely to cause complaint)
                - violations: list of {turn, rule, severity, explanation}
        """
        # ── Step 1: Normalize ──────────────────────────────────────────
        normalized = self.normalizer.normalize(conversation)

        # ── Step 2: Layer 1 — Deterministic checks ─────────────────────
        violations = []
        violations.extend(self.state_validator.check(normalized))
        violations.extend(self.timing_validator.check(normalized))
        violations.extend(self.amount_validator.check(normalized))

        # ── Step 3: Layer 2 — Gemini LLM judgment ──────────────────────
        if self.mode == "combined":
            violations.extend(self.llm_evaluator.check(normalized))
        else:
            violations.extend(self.compliance_evaluator.check(normalized))
            violations.extend(self.quality_evaluator.check(normalized))
            violations.extend(self.classification_checker.check(normalized))

        # ── Step 4: Conversation-level — loop detection ────────────────
        violations.extend(self._detect_loops(normalized))

        # ── Step 5: Aggregate scores ───────────────────────────────────
        quality_score = self._compute_quality_score(violations)
        risk_score = self._compute_risk_score(violations)

        # ── Step 6: Clean output format ────────────────────────────────
        clean_violations = [
            {
                "turn": v["turn"],
                "rule": v["rule"],
                "severity": v["severity"],
                "explanation": v["explanation"],
            }
            for v in violations
        ]

        return {
            "quality_score": round(quality_score, 3),
            "risk_score": round(risk_score, 3),
            "violations": clean_violations,
        }

    # ── Loop / Stuck Detection ─────────────────────────────────────────

    def _detect_loops(self, conv) -> list[dict]:
        """Detect near-identical repeated bot messages (Q5 violation).
        Uses difflib SequenceMatcher for fuzzy string similarity."""
        violations = []
        bot_messages = [
            (t.turn_number, t.text) for t in conv.bot_turns
        ]

        if len(bot_messages) < LOOP_MIN_REPEATS:
            return violations

        # Find clusters of similar bot messages
        seen_groups = []  # list of (representative_text, [turn_numbers])

        for turn_num, text in bot_messages:
            matched = False
            for group in seen_groups:
                similarity = SequenceMatcher(
                    None, group[0], text
                ).ratio()
                if similarity >= LOOP_SIMILARITY_THRESHOLD:
                    group[1].append(turn_num)
                    matched = True
                    break
            if not matched:
                seen_groups.append((text, [turn_num]))

        # Report groups with enough repeats
        for representative, turns in seen_groups:
            if len(turns) >= LOOP_MIN_REPEATS:
                # Severity scales with repetition count
                severity = min(1.0, 0.3 + len(turns) * 0.1)

                violations.append({
                    "turn": turns[0],
                    "rule": "Quality Q5 — Repetition / Stuck Loop",
                    "severity": round(severity, 2),
                    "category": "quality",
                    "explanation": (
                        f"Bot sent {len(turns)} near-identical messages "
                        f"(similarity ≥ {LOOP_SIMILARITY_THRESHOLD:.0%}). "
                        f"Affected turns: {turns}. "
                        f"Message: \"{representative[:80]}{'...' if len(representative) > 80 else ''}\". "
                        f"Agent appears stuck in a loop."
                    ),
                })

        return violations

    # ── Quality Score Computation ──────────────────────────────────────

    def _compute_quality_score(self, violations: list[dict]) -> float:
        """Compute quality score: start at 1.0, deduct based on violations.

        Formula: quality = max(0, 1.0 - Σ(severity × category_weight))
        """
        score = 1.0
        for v in violations:
            category = v.get("category", "quality")
            weight = CATEGORY_WEIGHTS.get(category, 0.1)
            score -= v["severity"] * weight

        return max(0.0, min(1.0, score))

    # ── Risk Score Computation ─────────────────────────────────────────

    def _compute_risk_score(self, violations: list[dict]) -> float:
        """Compute risk score: driven by worst-case violations.

        Logic:
        - Any critical violation (severity ≥ 0.9) → risk ≥ 0.8
        - Any high violation (severity ≥ 0.7) → risk ≥ 0.5
        - Otherwise: weighted sum of severities
        """
        if not violations:
            return 0.0

        max_severity = max(v["severity"] for v in violations)

        # Critical violations dominate
        if max_severity >= CRITICAL_SEVERITY:
            base_risk = 0.8
        elif max_severity >= HIGH_SEVERITY:
            base_risk = 0.5
        elif max_severity >= MODERATE_SEVERITY:
            base_risk = 0.3
        else:
            base_risk = 0.1

        # Add incremental risk from all violations
        incremental = sum(
            v["severity"] * 0.05 for v in violations
        )

        return min(1.0, base_risk + incremental)


def main():
    """Run evaluator on sample data for local testing."""
    evaluator = AgentEvaluator()

    # Try sample_conv.jsonl first, then production_logs
    data_path = Path("sample_conv.jsonl")
    if not data_path.exists():
        data_path = Path("data/production_logs.jsonl")

    if not data_path.exists():
        print("No data found. Make sure data/production_logs.jsonl exists.")
        return

    conversations = []
    with open(data_path) as f:
        for line in f:
            line = line.strip()
            if line:
                conversations.append(json.loads(line))

    limit = 10 if len(conversations) > 10 else len(conversations)
    print(f"Evaluating {limit} of {len(conversations)} conversations...\n")

    results = []
    for conv in conversations[:limit]:
        cid = conv["conversation_id"]
        print(f"  Evaluating {cid}...")

        try:
            result = evaluator.evaluate(conv)
            results.append(result)

            print(
                f"    quality={result['quality_score']:.3f}, "
                f"risk={result['risk_score']:.3f}, "
                f"violations={len(result['violations'])}"
            )

            # Print violation summaries
            for v in result["violations"]:
                sev_bar = "█" * int(v["severity"] * 10)
                print(
                    f"      [{sev_bar:<10}] Turn {v['turn']:>2}: "
                    f"{v['rule']}"
                )

            print()
        except Exception as e:
            print(f"    ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nEvaluated {len(results)} conversations.")

    # Summary statistics
    if results:
        avg_quality = sum(r["quality_score"] for r in results) / len(results)
        avg_risk = sum(r["risk_score"] for r in results) / len(results)
        total_violations = sum(len(r["violations"]) for r in results)
        print(f"  Avg quality: {avg_quality:.3f}")
        print(f"  Avg risk:    {avg_risk:.3f}")
        print(f"  Total violations: {total_violations}")


if __name__ == "__main__":
    main()
