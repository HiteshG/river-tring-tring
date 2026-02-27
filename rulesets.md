# Evaluation Rulesets — Complete Reference

All rules used by the Hybrid Evaluator, organized by dimension. Each rule has a fixed severity and maps to a specific section of the agent specification.

---

## Severity Scale

| Level | Range | Meaning |
|-------|-------|---------|
| **Critical** | 0.9–1.0 | Regulatory / invariant violation. Certain complaint or legal risk. |
| **High** | 0.7–0.8 | Spec violation likely to cause borrower harm or process failure. |
| **Medium-High** | 0.5–0.6 | Clear rule breach with moderate impact. |
| **Medium** | 0.4–0.5 | Process gap, may affect borrower experience. |
| **Low** | 0.1–0.3 | Minor imperfection, unlikely to cause harm. |

---

## 🧱 Dimension 1: State Integrity

Category weight in quality score: **0.25**

These enforce the state machine (Sections 2–5 of the spec). Violations are deterministic — no LLM needed.

| Rule ID | Rule Name | Spec Ref | Severity | Check Type | Description |
|---------|-----------|----------|----------|------------|-------------|
| S1 | Illegal State Transition | Section 4, Table 6 | 0.80 (High) | Deterministic | Transition not present in the allowed transition matrix. E.g., `new` → `intent_asked` skips required states. |
| S2 | Illegal Backward Transition | Invariant I1 | 0.80 (High) | Deterministic | Agent moved to an earlier state. Only exception: `settlement_explained`/`amount_pending` → `intent_asked` when classification = `unclear` + confidence = `low`. |
| S3 | Backward Exception Misuse | Section 4.7 | 0.80 (High) | Deterministic | Agent used the backward exception but conditions were not met (classification ≠ `unclear` or confidence ≠ `low`). |
| S4 | Exit State Violation | Invariant I2 | 1.00 (Critical) | Deterministic | Bot sent a message or triggered a transition after entering `escalated` or `dormant`. Exit states are final — no further activity allowed. |
| S5 | Action-State Mismatch | Invariant I4 | 0.80 (High) | Deterministic | Action called during wrong transition. E.g., `confirm_payment` called from `amount_sent` instead of `date_amount_asked`. |
| S6 | Missing Escalation | Section 4.3 | 0.80 (High) | Deterministic | Borrower classified as `disputes`, `refuses`, or `hardship` but conversation never transitioned to `escalated`. |
| S7 | ZCM Timeout Not Escalated | Section 4.6 | 0.80 (High) | Deterministic | `zcm_timeout` event occurred in `amount_pending` but conversation did not escalate. |
| S8 | Post-Exit Messages | Invariant I2 | 1.00 (Critical) | Deterministic | Bot sent automated messages after entering an exit state (`escalated`/`dormant`). |

### Valid Action-Transition Map

| Action | Required From State | Required To State |
|--------|-------------------|------------------|
| `request_settlement_amount` | `settlement_explained` | `amount_pending` |
| `send_settlement_amount` | `amount_pending` | `amount_sent` |
| `confirm_payment` | `date_amount_asked` | `payment_confirmed` |
| `escalate` | Any progression state | `escalated` |
| `zcm_timeout` | `amount_pending` | `escalated` |

---

## ⏱️ Dimension 2: Timing

Category weight in quality score: **0.10**

Pure timestamp math from Section 6.

| Rule ID | Rule Name | Spec Ref | Severity | Check Type | Description |
|---------|-----------|----------|----------|------------|-------------|
| T1 | Quiet Hours Violation | Section 6.1 | 0.60 (Medium-High) | Deterministic | Bot sent outbound message between 7 PM – 8 AM IST without a recent borrower message (within 30 min) to justify it as a reply. |
| T2 | Follow-Up Spacing | Section 6.2 | 0.50 (Medium) | Deterministic | Bot sent a follow-up message < 4 hours after a previous unanswered message. Agent should not bombard the borrower. |
| T3 | Missing Dormancy | Section 6.3 | 0.70 (High) | Deterministic | Borrower did not respond for > 7 days (10,080 min) but conversation was not marked `dormant`. |

### Quiet Hours Exemption
- **Allowed**: If the borrower sent a message during quiet hours and the bot is replying within 30 minutes, this is NOT a violation.

---

## 💰 Dimension 3: Amounts

Category weight in quality score: **0.15**

Financial validation from Section 9.

| Rule ID | Rule Name | Spec Ref | Severity | Check Type | Description |
|---------|-----------|----------|----------|------------|-------------|
| A1 | POS > TOS | Rule A1 | 0.80 (High) | Deterministic | POS (principal outstanding) exceeds TOS (total outstanding). Indicates data corruption — TOS should always be ≥ POS. |
| A2 | Settlement > TOS | Rule A3 | 0.80 (High) | Deterministic | Settlement offered exceeds the total outstanding. Settlement must be between floor and TOS. |
| A3 | Below Settlement Floor | Rule A4 | 0.60 (Medium-High) | Deterministic | Settlement offered < 70% of POS (assumed floor). Agent should counter with floor amount or escalate for ZCM approval. |
| A4 | Amount Inconsistency | Rule A5 | 0.60 (Medium-High) | Deterministic | Bot quoted conflicting settlement amounts without an intervening ZCM re-approval. Once quoted, amounts must remain consistent. |

### Key Relationships
```
Settlement Floor (70% POS) ≤ POS ≤ TOS
Settlement Floor ≤ Settlement Offered ≤ TOS
```

---

## 🛡️ Dimension 4: Compliance (LLM-Evaluated)

Category weight in quality score: **0.30**

Rubric: **1–5 scale** (highest weight — regulatory risk).

| Score | Label | Normalized Severity | Meaning |
|-------|-------|-------------------|---------|
| 1 | Clean | 0.00 | No compliance issue |
| 2 | Minor | 0.25 | Technically imperfect, unlikely to cause harm |
| 3 | Moderate | 0.50 | Clear gap, not immediately dangerous |
| 4 | Serious | 0.75 | Likely to cause borrower distress or complaint |
| 5 | Critical | 1.00 | Regulatory violation, certain complaint trigger |

| Rule ID | Rule Name | Spec Ref | Evaluated By | Description |
|---------|-----------|----------|--------------|-------------|
| C1 | Escalation Trigger Missed | Section 8.1 | Gemini LLM | Borrower expressed legal threats, DNC, abuse, or severe hardship but agent did not escalate. Requires semantic understanding of borrower language. |
| C2 | Hardship Handling Failure | Section 8.2 | Gemini LLM | Borrower disclosed financial hardship but agent failed to: (a) acknowledge with empathy, (b) avoided immediate payment push, (c) escalated if severe. |
| C3 | DNC Violation | Section 8.3 | Gemini LLM | Borrower explicitly asked to stop contact ("stop", "do not contact", "leave me alone") but agent did not immediately escalate or sent further messages. |
| C4 | Language Mismatch | Section 8.4 | Gemini LLM | Agent responded in a different language than the borrower's preferred language. E.g., English reply to a Hindi-speaking borrower. |
| C5 | Threats or Coercion | Section 8.5 | Gemini LLM | Agent used threatening, coercive, or intimidating language. Includes threats of legal action, property seizure, public embarrassment, or factually inaccurate consequences. |

### Escalation Trigger Keywords (Guidance for LLM)
- **Legal**: lawyer, court, RBI, TRAI, consumer forum, ombudsman, police, legal action
- **DNC**: stop, block, do not contact, leave me alone, unsubscribe
- **Abuse**: profanity, slurs, hostile language directed at agent
- **Severe Hardship**: job loss, medical emergency, death in family, hospitalization, accident

---

## 💬 Dimension 5: Quality (LLM-Evaluated)

Category weight in quality score: **0.10**

Rubric: **1–3 scale** (soft expectations, variable severity).

| Score | Label | Normalized Severity | Meaning |
|-------|-------|-------------------|---------|
| 1 | Good | 0.00 | Meets or exceeds expectations |
| 2 | Poor | 0.50 | Noticeable quality gap, affects borrower experience |
| 3 | Failing | 1.00 | Severe quality failure, conversation is broken |

| Rule ID | Rule Name | Spec Ref | Evaluated By | Description |
|---------|-----------|----------|--------------|-------------|
| Q1 | Inefficient Progress | Quality Q1 | Gemini LLM | Conversation takes too many turns without reaching `payment_confirmed` or an appropriate exit. Going in circles without progress. |
| Q2 | Classification Impact | Quality Q2 | Gemini LLM | Misclassifications of borrower intent negatively affected conversation flow — e.g., agent failed to recognize payment intent or hardship. |
| Q3 | Tone Mismatch | Quality Q3 | Gemini LLM | Agent tone doesn't match the situation. Transactional when borrower is distressed, aggressive with a cooperative borrower, dismissive of concerns. |
| Q4 | Context Loss | Quality Q4 | Gemini LLM | Agent re-asks answered questions, forgets prior context, or ignores information the borrower already provided. |
| Q5 | Repetition / Loop | Quality Q5 | Gemini LLM + Deterministic | Agent sends identical or near-identical messages. Deterministic check: SequenceMatcher similarity > 85% across ≥ 3 messages. LLM check: semantic repetition. Severity scales with count: `min(1.0, 0.3 + count × 0.1)`. |

---

## 🏷️ Dimension 6: Classification Accuracy (LLM-Evaluated)

Category weight in quality score: **0.10**

Rubric: **1–3 scale**.

| Score | Label | Normalized Severity | Meaning |
|-------|-------|-------------------|---------|
| 1 | Correct | 0.00 | Classification matches borrower's expressed intent |
| 2 | Debatable | 0.50 | Plausible but another label fits better |
| 3 | Wrong | 1.00 | Clearly misses actual intent, could cause wrong behavior |

| Rule ID | Rule Name | Spec Ref | Evaluated By | Description |
|---------|-----------|----------|--------------|-------------|
| CL1 | Individual Misclassification | Invariant I5 | Gemini LLM | A specific borrower message was incorrectly classified. E.g., "I want to settle" classified as `unclear`. |
| CL2 | Systematic Misclassification | Quality Q2 | Gemini LLM | More than 50% of borrower messages in the conversation were incorrectly classified. Indicates a systemic classification model issue. |

### Classification Categories Reference

| Classification | What It Means | Common Signals |
|---------------|---------------|----------------|
| `unclear` | Intent not determinable | Ambiguous, off-topic, single emoji |
| `wants_settlement` | Pay reduced amount to close loan | "settle", "discount", "reduce", "less" |
| `wants_closure` | Pay full amount to close loan | "full payment", "close account", "pay everything" |
| `refuses` | Refusing to pay | "I won't pay", "not paying", "refuse" |
| `disputes` | Disputing the debt | "I don't owe", "wrong amount", "already paid", "not my loan" |
| `hardship` | Financial difficulty | "lost my job", "medical emergency", "can't afford", "hospital" |
| `asks_time` | Asking for more time | "next month", "give me a week", "later", explicit date |

---

## Aggregation Formulas

### Quality Score
```
quality = max(0, 1.0 − Σ(severity × category_weight))
```
Higher = better. Deducted for every violation proportional to its severity and category importance.

### Risk Score
```
if max_severity ≥ 0.9:  risk = 0.8 + incremental
if max_severity ≥ 0.7:  risk = 0.5 + incremental
if max_severity ≥ 0.4:  risk = 0.3 + incremental
else:                    risk = 0.1 + incremental

incremental = Σ(severity × 0.05)
risk = min(1.0, risk)
```
Higher = more risky. Driven by worst-case violation, boosted by total violation count.

---

## Quick Reference: Severity by Spec Section

| Spec Section | What to Check | Severity |
|-------------|---------------|----------|
| Section 4 + Table 6 | Invalid state transition | High (0.8) |
| Section 7, Invariants I1-I5 | Invariant violation | Critical (1.0) |
| Section 6 | Timing violation | Medium–High (0.5–0.7) |
| Section 8 | Compliance failure | Critical (LLM 1–5 → 0.0–1.0) |
| Section 9 | Amount error | High (0.6–0.8) |
| Section 10 | Quality issue | Variable (LLM 1–3 → 0.0–1.0) |
