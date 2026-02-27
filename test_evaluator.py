"""
Test Evaluator
===============
Tests the AgentEvaluator against sample_conv.jsonl.

Conversation 1 (beea3aba): Known issues — repetition loop, stalled progress
Conversation 2 (6f6169fe): Clean happy-path conversation

Run: python test_evaluator.py
"""

import json
from pathlib import Path
from eval_takehome import AgentEvaluator


def load_sample_conversations():
    """Load conversations from sample_conv.jsonl."""
    path = Path("sample_conv.jsonl")
    conversations = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                conversations.append(json.loads(line))
    return conversations


def print_violations(violations, indent=4):
    """Pretty-print violation list."""
    prefix = " " * indent
    if not violations:
        print(f"{prefix}No violations found ✓")
        return

    for v in violations:
        sev_pct = f"{v['severity']:.0%}"
        print(f"{prefix}[{sev_pct:>4}] Turn {v['turn']:>2} | {v['rule']}")
        # Wrap explanation at 80 chars
        explanation = v["explanation"]
        if len(explanation) > 100:
            explanation = explanation[:97] + "..."
        print(f"{prefix}       {explanation}")
        print()


def test_conversation_1(evaluator, conv):
    """Test Conversation 1 (beea3aba) — should detect issues.

    Expected problems:
    - Repetition loop (turns 8-16): bot sends near-identical messages
    - Stalled progress: never reaches payment_confirmed
    - Possible classification issues
    """
    print("=" * 70)
    print(f"CONVERSATION 1: {conv['conversation_id']}")
    print(f"Language: {conv['metadata']['language']}, Turns: {conv['metadata']['total_turns']}")
    print("=" * 70)

    result = evaluator.evaluate(conv)

    print(f"\n  Quality Score: {result['quality_score']:.3f}")
    print(f"  Risk Score:    {result['risk_score']:.3f}")
    print(f"  Violations:    {len(result['violations'])}")
    print()

    print("  Violations:")
    print_violations(result["violations"])

    # Assertions
    errors = []

    # Should detect repetition loop
    loop_violations = [
        v for v in result["violations"]
        if "repetition" in v["rule"].lower() or "loop" in v["rule"].lower()
    ]
    if not loop_violations:
        errors.append("MISS: Did not detect repetition loop (turns 8-16)")

    # Quality should be low (conversation is broken)
    if result["quality_score"] > 0.6:
        errors.append(
            f"UNEXPECTED: Quality score {result['quality_score']:.3f} is too high "
            f"for a conversation stuck in a loop"
        )

    if errors:
        print("  ⚠ ISSUES:")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  ✓ All expected checks passed")

    return result


def test_conversation_2(evaluator, conv):
    """Test Conversation 2 (6f6169fe) — should be mostly clean.

    Expected:
    - Clean happy-path: new → message_received → verification → ...→ payment_confirmed
    - Few or no critical violations
    - Higher quality score
    """
    print("=" * 70)
    print(f"CONVERSATION 2: {conv['conversation_id']}")
    print(f"Language: {conv['metadata']['language']}, Turns: {conv['metadata']['total_turns']}")
    print("=" * 70)

    result = evaluator.evaluate(conv)

    print(f"\n  Quality Score: {result['quality_score']:.3f}")
    print(f"  Risk Score:    {result['risk_score']:.3f}")
    print(f"  Violations:    {len(result['violations'])}")
    print()

    print("  Violations:")
    print_violations(result["violations"])

    # Assertions
    errors = []

    # Should NOT have critical violations
    critical = [v for v in result["violations"] if v["severity"] >= 0.9]
    if critical:
        errors.append(
            f"UNEXPECTED: {len(critical)} critical violations in clean conversation"
        )

    # Quality should be reasonable
    if result["quality_score"] < 0.5:
        errors.append(
            f"UNEXPECTED: Quality score {result['quality_score']:.3f} seems too low "
            f"for a clean happy-path"
        )

    if errors:
        print("  ⚠ ISSUES:")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  ✓ All expected checks passed")

    return result


def main():
    print("Loading evaluator...")
    evaluator = AgentEvaluator()

    print("Loading sample conversations...")
    conversations = load_sample_conversations()

    if len(conversations) < 2:
        print(f"Expected 2 conversations, found {len(conversations)}")
        return

    print(f"Found {len(conversations)} conversations\n")

    # Test both conversations
    r1 = test_conversation_1(evaluator, conversations[0])
    print()
    r2 = test_conversation_2(evaluator, conversations[1])

    # Comparative summary
    print("\n" + "=" * 70)
    print("COMPARATIVE SUMMARY")
    print("=" * 70)
    print(f"  Conv 1 (loop):  quality={r1['quality_score']:.3f}  risk={r1['risk_score']:.3f}  violations={len(r1['violations'])}")
    print(f"  Conv 2 (clean): quality={r2['quality_score']:.3f}  risk={r2['risk_score']:.3f}  violations={len(r2['violations'])}")

    # The looping conversation should score worse
    if r1["quality_score"] < r2["quality_score"]:
        print("  ✓ Conv 1 (loop) scores lower quality than Conv 2 (clean)")
    else:
        print("  ⚠ Conv 1 should have lower quality than Conv 2")

    if r1["risk_score"] > r2["risk_score"]:
        print("  ✓ Conv 1 (loop) scores higher risk than Conv 2 (clean)")
    else:
        print("  ⚠ Conv 1 should have higher risk than Conv 2")


if __name__ == "__main__":
    main()
