# Writeup — Hybrid Agent Evaluator

## 1. Methodology

### The Core Problem

Evaluating a debt collection agent against a 30-page specification requires handling two fundamentally different kinds of rules:

- **Hard rules** that can be verified with exact logic (e.g., "transition from `new` to `payment_confirmed` is not in the allowed matrix")
- **Soft rules** that require understanding language, intent, and context (e.g., "did the agent respond with appropriate empathy to hardship?")

A purely deterministic system misses all soft violations. A purely LLM system wastes tokens on things checkable with an `if` statement — and LLMs are unreliable on structured reasoning (transition matrices, timestamp arithmetic). The solution is a **two-layer hybrid**.

### Mapping Spec to Code

Every checkable rule was traced to a specific spec section and implemented in the appropriate layer:

| Spec Section | Rule Type | Layer | Implementation |
|-------------|-----------|-------|----------------|
| Section 4 (State Machine) | Transition matrix, invariants I1/I2/I4 | Deterministic | `state_validator.py` — 6 checks |
| Section 4.3 (Escalation) | Escalation triggers for disputes/hardship | Deterministic | `state_validator.py` — missing escalation |
| Section 6 (Timing) | Quiet hours, follow-up spacing, dormancy | Deterministic | `timing_validator.py` — 3 checks |
| Section 9 (Amounts) | POS/TOS consistency, settlement floor | Deterministic | `amount_validator.py` — 4 checks |
| Section 8 (Compliance) | Empathy, DNC, language, threats | LLM (Gemini) | 1–5 rubric, 5 compliance dimensions |
| Section 10 (Quality) | Progress, tone, context, repetition | LLM (Gemini) | 1–3 rubric, Q1–Q5 |
| Invariant I5 (Classification) | Intent classification accuracy | LLM (Gemini) | 1–3 rubric per message |

**Preprocessing** merges four parallel data arrays (messages, classifications, transitions, function_calls) into a single per-turn timeline (`NormalizedConversation`), so every validator sees a consistent view of each turn with its classification, state, and timing attached.

**Scoring** uses two models: (1) **Quality** — deduction from 1.0, weighted by category (compliance 30%, state integrity 25%, amounts 15%, timing 10%, quality 10%, classification 10%); (2) **Risk** — driven by worst single violation (one DNC breach = high risk regardless of everything else), then boosted by total count.

### Why Rubrics, Not Binary

The spec explicitly leaves room for judgment ("what counts as appropriate empathy?" is open by design). Binary pass/fail would force false precision. Rubrics (1–5 for compliance, 1–3 for quality) capture the gradient: a slightly cold tone (2/3) is different from a threatening message (5/5).

---

## 2. Annotator Disagreement

### Who Are the Annotators?

The three annotators are LLM-based, each with different underlying models:

| Annotator | Model | Annotations | Avg Quality Score | Avg Failure Points |
|-----------|-------|------------:|------------------:|-------------------:|
| Annotator 1 | Claude Sonnet 4 | 200 | 0.337 | 7.8 |
| Annotator 2 | GPT-4o-mini | 200 | 0.596 | 2.5 |
| Annotator 3 | Gemini 2.0 Flash | 200 | 0.443 | 4.9 |

100 conversations were annotated by all three, enabling direct comparison.

### Key Disagreement Patterns

**Leniency gradient**: GPT-4o-mini is substantially more lenient (avg 0.596 vs Claude's 0.337). On the 100 overlapping conversations, the average score spread is **0.288** — meaning annotators routinely disagree by ~30 points on a 0–1 scale. The worst disagreements reach 0.52 spread (e.g., `2c94dd50`: Claude scores 0.28, GPT-4o-mini scores 0.80).

**Risk flag calibration**: Claude flags compliance concerns in 97% of its annotations; GPT-4o-mini flags them in 49%. This isn't because Claude is wrong — it's because Claude has a **lower threshold** for what constitutes a concern. Gemini falls in between.

| Risk Flag | Annotator 1 (Claude) | Annotator 2 (GPT-4o) | Annotator 3 (Gemini) |
|-----------|---------------------:|----------------------:|---------------------:|
| compliance_concern | 194 (97%) | 97 (49%) | 53 (27%) |
| tone_inappropriate | 127 (64%) | 60 (30%) | 65 (33%) |
| hardship_ignored | 117 (59%) | 127 (64%) | 26 (13%) |
| escalation_missed | 114 (57%) | 31 (16%) | 74 (37%) |
| stop_request_missed | 46 (23%) | 34 (17%) | 20 (10%) |

**What they agree on**: All three consistently flag DNC violations and blatant loops. What they disagree on is **severity of soft failures** — a tone issue that Claude calls serious, GPT-4o-mini calls minor.

### How I Handle Disagreement

My evaluator doesn't try to replicate any single annotator. Instead, it uses **deterministic checks as ground truth** for hard rules (no annotation needed — the transition matrix is either violated or not), and treats LLM-evaluated soft rules as **signal with uncertainty**. The rubric-based scoring naturally produces a range rather than a binary, which maps better to the reality that annotators disagree on severity.

For validation, I compare my evaluator's output distribution against all three annotators rather than optimizing for agreement with any one.

---

## 3. Findings

### What the Agent Does Wrong (80-conversation sample)

**100% of conversations have at least one violation** — avg 10.0 violations per conversation, avg quality score 0.238/1.0.

**The #1 problem is classification accuracy** (39.1% of all violations). The bot systematically classifies clear borrower intents as `unclear` — "I want to settle" gets classified as `unclear`, "I don't owe this" gets classified as `unclear`. This cascades: wrong classification → wrong state transition → wrong response → borrower frustration. This is a fixable upstream issue.

**State invariant violations are the most severe** — Invariant I2 (exit states are final) is violated in 58 instances. The bot continues sending messages after entering the `escalated` state. This is a critical bug: once escalated, the bot should go silent.

**Escalation failures are near-critical** (severity 0.97) — in 38 cases, the bot failed to escalate when it should have (disputes, DNC requests, hardship). These directly correlate with complaints and regulatory flags.

### What Predicts Bad Outcomes?

| Outcome | Avg Violations | Avg Quality | Key Differentiator |
|---------|---------------:|------------:|--------------------|
| Payment received (n=26) | 7.1 | 0.387 | Fewer violations, higher quality |
| No payment (n=54) | 11.4 | 0.167 | 60% more violations |
| Complained (n=5) | 9.0 | 0.296 | Compliance + repetition violations overrepresented |
| Regulatory flag (n=22) | 6.7 | 0.450 | Flagged convs actually show *fewer* violations — but different types |

**Language matters**: Hindi conversations average 11.4 violations vs English at 8.4. The bot handles English conversations better, suggesting language-specific prompt tuning is needed.

**DPD is the strongest predictor**: Conversations with DPD > 180 average 13.0 violations and quality 0.052 — the bot essentially fails on deep-delinquency cases. These borrowers are more hostile, and the bot doesn't adapt.

---

## 4. Limitations

**LLM-as-judge limitations**: My Layer 2 evaluator (Gemini) has the same problem as the annotators — it's an LLM judging an LLM. On borderline compliance cases, Gemini occasionally misses findings that the separate-call mode catches. The combined-prompt approach (1 call vs 3) trades ~5% compliance sensitivity for 3x speed.

**Settlement floor assumption**: The spec references a settlement floor but doesn't provide it in the data. I assumed 70% of POS based on industry norms. If the actual floor is different, this affects amount violation counts.

**No access to audio/original media**: Voice-to-text artifacts appear in the data, but I can't verify whether the bot's response was appropriate for the original audio — I only see the transcription.

**Sample size for outcome correlations**: Only 5 complaints in the 80-conversation sample. The correlations are directional but not statistically significant at this sample size. A full 700-conversation run would strengthen these.

**Attribution ambiguity**: `channel_attribution` is "uncertain" for many conversations. Whether a violation *caused* a bad outcome or merely co-occurred is unclear — most borrowers interact through multiple channels simultaneously.

---

## 5. If I Had 3 Months

### Month 1: Reliable Eval Infrastructure

- **Ground truth dataset**: Have human compliance officers annotate 200 conversations as gold standard. Measure inter-annotator agreement (Krippendorff's alpha). Use this to calibrate both the LLM evaluator and the three existing annotators.
- **Continuous eval pipeline**: Run the evaluator on every conversation in real-time (not batch). Store results in a database with dashboards for trend monitoring.
- **A/B test the evaluator**: Compare evaluator scores against actual complaint/escalation outcomes. Tune the severity weights using logistic regression on `borrower_complained` as the target.

### Month 2: Close the Loop

- **Classification model retraining**: The #1 finding is classification failures. Feed the evaluator's misclassification data back as training signal. Flag conversations where the bot classified `unclear` but the evaluator (and ground truth) classify otherwise.
- **Prompt-level feedback**: For quality issues (tone, repetition, context), generate specific prompt patches. E.g., "when DPD > 180, use de-escalation tone template instead of standard collection template."
- **Automated escalation audit**: Build a real-time check that flags conversations the evaluator scores as risk > 0.7 for immediate human review — before the borrower complains.

### Month 3: Scale and Harden

- **Multi-model ensemble**: Run 3 LLM evaluators (Claude, GPT-4o, Gemini) in parallel. Use agreement as confidence — when all 3 agree on a violation, it's near-certain. When they disagree, flag for human review.
- **Drift detection**: Monitor violation rates weekly. If classification accuracy drops or a new compliance pattern emerges, trigger alerts.
- **Cost optimization**: Cache LLM evaluations for similar conversations. Use embedding similarity to identify clusters and evaluate representatives instead of every conversation.
- **Regression testing**: Maintain a set of "known bad" conversations. After any agent update, re-run this set to verify fixes don't regress.
