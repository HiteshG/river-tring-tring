# Riverline Agent Evaluator

## States 
![Mermaid Diagram](https://raw.githubusercontent.com/HiteshG/river-tring-tring/main/mermaid-diagram.png)

Hybrid evaluation system for WhatsApp debt collection conversations. Combines deterministic rule checks with Gemini LLM judgment to produce quality scores, risk scores, and violation reports.

## Architecture

```
Raw Conversation JSON
        │
        ▼
  Event Normalizer          ← Merge messages + classifications + transitions
        │
   ┌────┴────┐
   ▼         ▼
Layer 1    Layer 2
Determ.    Gemini LLM
   │         │
   └────┬────┘
        ▼
   Aggregator               ← quality_score, risk_score, violations[]
```

**Layer 1 (Deterministic)**: State transitions, timing, amounts, loop detection — exact logic, no LLM.  
**Layer 2 (Gemini LLM)**: Compliance (1–5 rubric), quality (1–3 rubric), classification accuracy (1–3 rubric).

Full architecture explanation → [`writeup.md`](writeup.md)

## Quick Start

**No dependencies required** — uses only Python standard library + Gemini API via `urllib`.

```bash
# 1. Evaluate a random sample of conversations
python3 run_evaluation.py --sample 80 --mode separate --seed 42

# 2. Generate the violations report
python3 generate_violations_report.py
```

## Commands

### `run_evaluation.py` — Evaluate Conversations

```bash
# Evaluate all 700 conversations (combined mode, fast)
python3 run_evaluation.py

# Random sample of 80 conversations (separate mode, thorough)
python3 run_evaluation.py --sample 80 --mode separate --seed 42

# First 50 conversations sequentially
python3 run_evaluation.py --limit 50

# Resume interrupted run
python3 run_evaluation.py --resume

# Adjust concurrency
python3 run_evaluation.py --sample 100 --workers 3
```

| Flag | Description |
|------|-------------|
| `--mode combined\|separate` | `combined` = 1 LLM call (fast), `separate` = 3 LLM calls (thorough) |
| `--sample N` | Randomly sample N conversations |
| `--seed N` | Random seed for reproducible sampling |
| `--limit N` | Evaluate first N conversations (sequential) |
| `--resume` | Skip already-evaluated conversations |
| `--workers N` | Concurrent workers (default: 5) |

### `generate_violations_report.py` — Generate Report

```bash
python3 generate_violations_report.py
```

Reads `violation_rating.jsonl` + outcomes + metadata → produces `violations.md`.

### `test_evaluator.py` — Test on Sample Conversations

```bash
python3 test_evaluator.py
```

Tests against `sample_conv.jsonl` to verify evaluator logic.

## File Structure

```
riverline/
├── eval_takehome.py              # Main evaluator (AgentEvaluator class)
├── normalizer.py                 # Preprocessing: raw JSON → per-turn timeline
├── run_evaluation.py             # Batch runner (concurrent, resumable)
├── generate_violations_report.py # Violations analysis → violations.md
├── test_evaluator.py             # Test harness
│
├── validators/                   # Layer 1: Deterministic
│   ├── state_validator.py        #   6 state machine checks
│   ├── timing_validator.py       #   3 timing checks
│   └── amount_validator.py       #   4 amount checks
│
├── evaluators/                   # Layer 2: Gemini LLM
│   ├── gemini_client.py          #   API client (rate limiting, retries)
│   ├── combined_evaluator.py     #   Single-call mode (fast)
│   ├── compliance_evaluator.py   #   Separate compliance eval
│   ├── quality_evaluator.py      #   Separate quality eval
│   └── classification_checker.py #   Separate classification check
│
├── prompts/                      # All LLM prompt templates
│   ├── compliance_prompt.py      #   Section 8 (1-5 rubric)
│   ├── quality_prompt.py         #   Section 10 (1-3 rubric)
│   ├── classification_prompt.py  #   Invariant I5 (1-3 rubric)
│   └── combined_prompt.py        #   All three merged
│
├── data/
│   ├── production_logs.jsonl     # 700 conversations (input)
│   ├── outcomes.jsonl            # 30-60 day outcomes
│   └── annotations/             # 3 annotator labels
│       ├── annotator_1.jsonl     #   Claude Sonnet
│       ├── annotator_2.jsonl     #   GPT-4o-mini
│       └── annotator_3.jsonl     #   Gemini Flash
│
├── violation_rating.jsonl        # Per-conversation eval results (output)
├── violations.md                 # Violations analysis report (output)
├── writeup.md                    # Design writeup (methodology, findings)
└── rulesets.md                   # Complete rule reference
```

## Output

| File | Description |
|------|-------------|
| `violation_rating.jsonl` | One JSON per conversation: `quality_score`, `risk_score`, `violations[]` |
| `violations.md` | Statistical analysis: common violations, outcome correlations, segment breakdown, examples |
| `writeup.md` | Methodology, annotator disagreement, findings, limitations, production roadmap |
