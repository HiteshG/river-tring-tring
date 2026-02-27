# Hybrid Evaluator — Walkthrough

## Architecture Implemented

```
riverline/
├── eval_takehome.py              # Orchestrator + aggregator
├── normalizer.py                 # Per-turn structured extraction
├── validators/                   # Layer 1: Deterministic
│   ├── state_validator.py        # 6 checks (transitions, invariants)
│   ├── timing_validator.py       # 3 checks (quiet hours, spacing, dormancy)
│   └── amount_validator.py       # 4 checks (POS/TOS, floor=70% POS)
├── evaluators/                   # Layer 2: Gemini LLM
│   ├── gemini_client.py          # API client (structured JSON output)
│   ├── compliance_evaluator.py   # Rubric 1-5 (escalation, DNC, hardship)
│   ├── quality_evaluator.py      # Rubric 1-3 (Q1-Q5)
│   └── classification_checker.py # Rubric 1-3 (intent accuracy)
└── test_evaluator.py             # Test harness
```

---

## Test Results

### Conversation 1 — `beea3aba` (Repetition Loop)

| Metric | Value |
|--------|-------|
| **Quality Score** | **0.125** |
| **Risk Score** | **1.000** |
| **Violations** | **10** |

| Sev | Turn | Rule | Finding |
|-----|------|------|---------|
| 0.75 | 7 | Compliance: escalation_trigger | Borrower said "Call me later" repeatedly — agent should have recognized refusal pattern |
| 1.00 | 8 | Q1 — Efficient Progress | Conversation stuck in loop from turn 8+, zero progress |
| 0.50 | 8 | Q2 — Classification Impact | "Can't say now" classified as `unclear`, preventing resolution |
| 0.50 | 8 | Q3 — Tone | Bot responds "Great." when borrower cannot commit — tone mismatch |
| 1.00 | 9 | Q4 — Context Retention | Bot ignores borrower's "next month" and "can't promise" repeatedly |
| 1.00 | 8 | Q5 — Repetition (LLM) | Bot repeats exact same message 8 times |
| 0.50 | 5,6,7 | Classification Accuracy | `asks_time` debatable for vague deferral statements |
| 1.00 | 8 | Q5 — Loop (deterministic) | 8 near-identical messages detected (similarity ≥ 85%) |

### Conversation 2 — `6f6169fe` (Happy Path)

| Metric | Value |
|--------|-------|
| **Quality Score** | **0.550** |
| **Risk Score** | **1.000** |
| **Violations** | **6** |

| Sev | Turn | Rule | Finding |
|-----|------|------|---------|
| 0.50 | 5 | Q1 — Efficient Progress | Slight stall at turn 5 before options |
| 0.50 | 1 | Q2 — Classification Impact | Clear messages classified as `unclear` repeatedly |
| 0.50 | 5 | Q4 — Context Retention | Bot didn't address borrower's direct question about options |
| 1.00 | 5 | Classification Accuracy | "I do want to pay it off" → `unclear` (should be `wants_settlement`) |
| 1.00 | 8 | Classification Accuracy | "That works for me" → `unclear` (should be `wants_settlement`) |
| 1.00 | 9 | Classification Accuracy | "I should be able to pay by Friday" → `unclear` (should be `asks_time`) |

---

## Comparative Summary

| | Conv 1 (Loop) | Conv 2 (Happy Path) |
|--|--------------|-------------------|
| Quality | **0.125** (broken) | **0.550** (moderate) |
| Risk | 1.000 | 1.000 |
| Violations | 10 | 6 |
| Layer 1 hits | Loop detection | None |
| Layer 2 hits | Compliance, all Q1-Q5, classification | Q1, Q2, Q4, classification |

> [!NOTE]
> Conv 2's risk score is high due to critical misclassification violations (severity 1.0). This is correct — classifying "I want to pay" as `unclear` is a real risk because it could cause the agent to miss an opportunity or misroute the borrower.

## What Works

- **Layer 1** deterministic loop detection catches the 8-message repetition in Conv 1
- **Layer 2** LLM judgment catches nuanced issues: tone mismatch ("Great." after "can't promise"), escalation gaps, context loss
- **Classification checker** correctly identifies all misclassified messages in both conversations
- Scoring correctly **differentiates** broken (0.125) from functional (0.550) conversations
