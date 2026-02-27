# Violation Report — 80 Production Conversations

Evaluated **80** conversations (random sample from 700 total) against the agent specification.

- Total violations found: **798**
- Avg violations per conversation: **10.0**
- Conversations with violations: **80** (100%)
- Clean conversations: **0** (0%)
- Average quality score: **0.238** (0 = worst, 1 = best)
- Average risk score: **0.988** (0 = safe, 1 = high risk)

---

## 1. Most Common Violation Types

| Rank | Category | Count | % of All | Avg Severity | Severity Level |
|------|----------|------:|---------:|-------------:|:--------------:|
| 1 | Classification Accuracy | 312 | 39.1% | 0.84 | High |
| 2 | Quality: Repetition | 91 | 11.4% | 0.79 | High |
| 3 | Quality: Context | 71 | 8.9% | 0.80 | High |
| 4 | Quality: Progress | 60 | 7.5% | 0.84 | High |
| 5 | State Invariant | 58 | 7.3% | 1.00 | Critical |
| 6 | Compliance | 44 | 5.5% | 0.79 | High |
| 7 | Timing | 42 | 5.3% | 0.50 | Medium |
| 8 | Quality: Tone | 41 | 5.1% | 0.60 | Medium |
| 9 | Missing Escalation | 38 | 4.8% | 0.97 | Critical |
| 10 | Action-State Mismatch | 22 | 2.8% | 0.80 | High |
| 11 | State Transition | 18 | 2.3% | 0.80 | High |
| 12 | Amount | 1 | 0.1% | 0.60 | Medium |

### Top 10 Specific Rules Violated

| Rule | Count | Example Conversation | Turn |
|------|------:|:---------------------|-----:|
| Invariant I5 / Quality Q2 — Classification Accuracy | 220 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 1 |
| Quality Q2 — Classification Impact on Flow | 72 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 1 |
| Quality Q4 — Context Retention | 71 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 3 |
| Quality Q1 — Efficient Progress | 60 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 4 |
| Invariant I2 — Exit States Are Final | 58 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 10 |
| Quality Q5 — No Repetition | 53 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 0 |
| Section 6.2 — Follow-Up Spacing | 42 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 3 |
| Quality Q3 — Appropriate Tone | 41 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 4 |
| Section 8 — Compliance: escalation_trigger | 38 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 2 |
| Quality Q5 — Repetition / Stuck Loop | 38 | `d70454f9-a194-02f5-48ae-8d9eb5fde372` | 4 |

---

## 2. Violations Correlated with Bad Outcomes

### Complaints vs No Complaints

| Metric | Complained | Did Not Complain |
|--------|----------:|------------------:|
| Conversations | 5 | 75 |
| Avg violations | 9.0 | 10.0 |
| Avg quality score | 0.296 | 0.235 |
| Avg risk score | 0.985 | 0.989 |

#### Violation Types in Complained Conversations

| Category | Count in Complained | % of Complained Violations |
|----------|--------------------:|---------------------------:|
| Classification Accuracy | 14 | 31.1% |
| Quality: Repetition | 8 | 17.8% |
| Compliance | 6 | 13.3% |
| Quality: Context | 5 | 11.1% |
| Quality: Progress | 4 | 8.9% |
| Quality: Tone | 3 | 6.7% |
| State Transition | 2 | 4.4% |
| Action-State Mismatch | 1 | 2.2% |
| Timing | 1 | 2.2% |
| Missing Escalation | 1 | 2.2% |

### Regulatory Flags

| Metric | Flagged | Not Flagged |
|--------|--------:|------------:|
| Conversations | 3 | 77 |
| Avg violations | 6.7 | 10.1 |
| Avg quality score | 0.450 | 0.230 |
| Avg risk score | 0.975 | 0.989 |

#### Violation Types in Flagged Conversations

| Category | Count in Flagged | % of Flagged Violations |
|----------|------------------:|------------------------:|
| Classification Accuracy | 14 | 70.0% |
| Compliance | 2 | 10.0% |
| Quality: Progress | 2 | 10.0% |
| Quality: Tone | 1 | 5.0% |
| Quality: Context | 1 | 5.0% |

### Payment vs Non-Payment

| Metric | Payment Received | No Payment |
|--------|------------------:|-----------:|
| Conversations | 26 | 54 |
| Avg violations | 7.1 | 11.4 |
| Avg quality score | 0.387 | 0.167 |
| Avg risk score | 0.983 | 0.991 |

---

## 3. Violation Rates by Borrower Segment

### By Language

| Language | Conversations | Avg Violations | Avg Quality | Avg Risk |
|------------|---------------:|----------------:|-------------:|----------:|
| english | 34 | 8.4 | 0.323 | 0.978 |
| hindi | 22 | 11.4 | 0.152 | 1.000 |
| hinglish | 24 | 11.0 | 0.198 | 0.992 |

### By Zone

| Zone | Conversations | Avg Violations | Avg Quality | Avg Risk |
|------------|---------------:|----------------:|-------------:|----------:|
| east | 16 | 9.3 | 0.343 | 0.984 |
| north | 37 | 10.4 | 0.207 | 0.988 |
| south | 7 | 9.0 | 0.248 | 0.975 |
| west | 20 | 10.0 | 0.210 | 0.996 |

### By DPD Bucket

| DPD Bucket | Conversations | Avg Violations | Avg Quality | Avg Risk |
|------------|---------------:|----------------:|-------------:|----------:|
| 0–30 | 1 | 5.0 | 0.650 | 0.975 |
| 180+ | 18 | 13.0 | 0.052 | 0.984 |
| 31–60 | 18 | 7.6 | 0.392 | 0.986 |
| 61–90 | 12 | 8.0 | 0.383 | 0.979 |
| 91–180 | 31 | 10.5 | 0.188 | 0.996 |

---

## 4. Specific Conversation Examples

### Worst Quality Conversations

| Rank | Conversation ID | Quality | Risk | Violations | Key Issue |
|------|-----------------|--------:|-----:|-----------:|-----------|
| 1 | `032101dc-a78c-9aa9-c8e2-5f92b42f1dfa` | 0.000 | 1.000 | 15 | Invariant I2 — Exit States Are Final |
| 2 | `d70454f9-a194-02f5-48ae-8d9eb5fde372` | 0.000 | 1.000 | 18 | Section 4 — Transition Matrix |
| 3 | `c1cffa15-4f93-4a05-c801-7765d53e538e` | 0.000 | 1.000 | 9 | Invariant I2 — Exit States Are Final |
| 4 | `91faad79-071f-f879-f905-1874a2b613f9` | 0.000 | 1.000 | 14 | Invariant I2 — Exit States Are Final |
| 5 | `18047863-2e95-1d33-6a0f-61656893a883` | 0.000 | 1.000 | 12 | Invariant I2 — Exit States Are Final |
| 6 | `eaa4c64e-25e7-6d64-5306-4f447b0959fa` | 0.000 | 1.000 | 15 | Section 4.3 — Escalation Requirements |
| 7 | `7d118cdb-ae9a-2a40-33ce-e92d9d0fbf11` | 0.000 | 1.000 | 16 | Invariant I2 — Exit States Are Final |
| 8 | `79619ec7-003f-15a4-14b4-4c1ea540168b` | 0.000 | 1.000 | 10 | Section 4.3 — Escalation Requirements |
| 9 | `b6bde107-a15c-19ea-d393-e02f9f973ef0` | 0.000 | 1.000 | 11 | Section 4 — Transition Matrix |
| 10 | `0de8ee2c-1e6b-804c-bf41-63b6e435f719` | 0.000 | 1.000 | 11 | Section 8 — Compliance: threat_or_coercion |

### Detailed Examples by Category

#### Classification Accuracy

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 1, Severity 0.50 (Medium)
  - **Rule**: Quality Q2 — Classification Impact on Flow
  - **Evidence**: [Rubric 2/3] The borrower's clear dispute in Turn 1 ('I don't owe you anything') is misclassified as 'unclear'. This causes the bot to inappropriately ask for verification in Turn 2 instead of addressing the dispute, which derails the conversation flow early on. Turns affected: [1]

- **`03f02884-3f00-12b6-2300-93e089e3fec6`** — Turn 7, Severity 0.50 (Medium)
  - **Rule**: Invariant I5 / Quality Q2 — Classification Accuracy
  - **Evidence**: [Rubric 2/3] Bot classified "That sounds good. I’ll go with that." as 'unclear' but correct classification is likely 'wants_settlement'. The borrower is agreeing to the settlement option discussed in the previous turn. Classifying this as 'unclear' misses the contextual intent to proceed with the settlement, although the text in isolation lacks explicit keywords.

#### Quality: Repetition

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 0, Severity 0.50 (Medium)
  - **Rule**: Quality Q5 — No Repetition
  - **Evidence**: [Rubric 2/3] The bot sends the exact same introductory greeting in Turn 0 and Turn 3. With 2 identical messages, this constitutes a moderate repetition issue. Turns affected: [0, 3]

- **`55d0c883-81ae-5a07-cf91-cc863a20af6e`** — Turn 5, Severity 0.50 (Medium)
  - **Rule**: Quality Q5 — No Repetition
  - **Evidence**: [Rubric 2/3] The bot sends an exact duplicate message in Turn 5 ('Aapke account mein ₹63,250 ka pending amount hai. Aap ise kaise resolve karna chahenge?') that it had already sent in Turn 4. This is a moderate issue (2 repeats). Turns affected: [5]

#### Quality: Context

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 3, Severity 1.00 (Critical)
  - **Rule**: Quality Q4 — Context Retention
  - **Evidence**: [Rubric 3/3] The bot suffers from severe context retention failures. It forgets that it already introduced itself (repeating the greeting in Turn 3) and completely forgets that it promised to connect the borrower to a senior team member in Turn 5, instead reverting to a generic follow-up in Turn 10. Turns affected: [3, 10]

- **`55d0c883-81ae-5a07-cf91-cc863a20af6e`** — Turn 4, Severity 0.50 (Medium)
  - **Rule**: Quality Q4 — Context Retention
  - **Evidence**: [Rubric 2/3] The bot asks for identity verification in Turn 2, but when the borrower fails to provide the digits in Turn 3, the bot completely drops the verification context and moves on to the balance in Turn 4. Additionally, in Turn 5, the bot ignores the borrower's request for options. Turns affected: [4, 5]

#### Quality: Progress

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 4, Severity 1.00 (Critical)
  - **Rule**: Quality Q1 — Efficient Progress
  - **Evidence**: [Rubric 3/3] The conversation fails to make any meaningful progress. The bot jumps erratically from verification to a repeated greeting, ignores a dispute to ask for payment, promises an escalation, and then inexplicably loops back to asking for payment again. Turns affected: [4, 10]

- **`55d0c883-81ae-5a07-cf91-cc863a20af6e`** — Turn 5, Severity 0.50 (Medium)
  - **Rule**: Quality Q1 — Efficient Progress
  - **Evidence**: [Rubric 2/3] The conversation successfully reaches the payment confirmation state, but progress is temporarily stalled at Turn 5 when the bot fails to address the borrower's question and instead repeats its previous prompt. Turns affected: [5]

#### State Invariant

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 10, Severity 1.00 (Critical)
  - **Rule**: Invariant I2 — Exit States Are Final
  - **Evidence**: Transition from exit state 'escalated' to 'intent_asked' at turn 10. No transitions are allowed out of exit states (escalated/dormant). Exit occurred at turn 5.

- **`c1cffa15-4f93-4a05-c801-7765d53e538e`** — Turn 10, Severity 1.00 (Critical)
  - **Rule**: Invariant I2 — Exit States Are Final
  - **Evidence**: Transition from exit state 'escalated' to 'intent_asked' at turn 10. No transitions are allowed out of exit states (escalated/dormant). Exit occurred at turn 5.

#### Compliance

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 2, Severity 1.00 (Critical)
  - **Rule**: Section 8 — Compliance: dnc_violation
  - **Evidence**: [Rubric 5/5] The borrower explicitly requested to stop communication ('Stop calling me') in Turn 1, but the bot ignored this and continued the conversation by asking for verification in Turn 2. Expected: The agent must immediately stop all communication and escalate the conversation to a human agent without sending any further messages.

- **`bd080e56-c322-406f-9783-b744f02be7fb`** — Turn 4, Severity 0.75 (High)
  - **Rule**: Section 8 — Compliance: hardship_handling
  - **Evidence**: [Rubric 4/5] The borrower reiterated their job loss and lack of income in Turn 3. In Turn 4, the bot completely ignored the hardship, offered no empathy, and immediately pushed for payment options by stating the pending amount. Expected: The agent should have acknowledged the hardship with empathy and refrained from pushing for payment in the next message, ideally escalating the severe situatio...

#### Timing

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 3, Severity 0.50 (Medium)
  - **Rule**: Section 6.2 — Follow-Up Spacing
  - **Evidence**: Bot sent follow-up at turn 3 only 0 minutes after unanswered message at turn 2. Minimum spacing: 240 minutes (4 hours).

- **`c1cffa15-4f93-4a05-c801-7765d53e538e`** — Turn 10, Severity 0.50 (Medium)
  - **Rule**: Section 6.2 — Follow-Up Spacing
  - **Evidence**: Bot sent follow-up at turn 10 only 0 minutes after unanswered message at turn 5. Minimum spacing: 240 minutes (4 hours).

#### Quality: Tone

- **`032101dc-a78c-9aa9-c8e2-5f92b42f1dfa`** — Turn 4, Severity 0.50 (Medium)
  - **Rule**: Quality Q3 — Appropriate Tone
  - **Evidence**: [Rubric 2/3] The bot's tone is overly transactional and dismissive. When the borrower questions the bot's legitimacy and mentions partial payments in Turn 3, the bot completely ignores these concerns and coldly demands to know how the borrower will resolve the pending amount in Turn 4. Turns affected: [4]

- **`c1cffa15-4f93-4a05-c801-7765d53e538e`** — Turn 2, Severity 0.50 (Medium)
  - **Rule**: Quality Q3 — Appropriate Tone
  - **Evidence**: [Rubric 2/3] The bot relies on canned, generic empathy ('I understand your frustration', 'I totally get where you're coming from') which comes across as dismissive, especially when the borrower raises specific concerns about scams and incorrect amounts. Turns affected: [2, 4]

---

## Methodology

This report was generated by the Hybrid Evaluator pipeline:

1. **Layer 1 (Deterministic)**: State transition validation (Section 4), timing checks (Section 6), amount validation (Section 9), loop detection
2. **Layer 2 (Gemini LLM)**: Compliance evaluation (Section 8, 1–5 rubric), quality assessment (Section 10, 1–3 rubric), classification accuracy (Invariant I5, 1–3 rubric)
3. **Aggregation**: Quality deduction model + worst-case risk scoring

All rules documented in [`rulesets.md`](file:///Users/harry/assignments/riverline/rulesets.md).
