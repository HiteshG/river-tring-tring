"""
Classification Accuracy Prompt Template
========================================
Invariant I5 — Borrower intent classification verification.
Rubric: 1-3 scale (Correct → Wrong).

Used by: ClassificationChecker (separate mode), CombinedLLMEvaluator (embedded)
"""

CLASSIFICATION_PROMPT_TEMPLATE = """You are checking whether a debt collection bot correctly classified borrower messages.

## Classification Categories (from spec Section 3)

Every borrower message must be classified into exactly one of these categories:

| Classification    | What it means |
|-------------------|---------------|
| unclear           | Borrower's intent could not be determined |
| wants_settlement  | Borrower wants to pay a reduced amount to close the loan |
| wants_closure     | Borrower wants to pay the full amount to close the loan |
| refuses           | Borrower is refusing to pay |
| disputes          | Borrower is disputing the debt or amount owed |
| hardship          | Borrower reporting financial difficulty (job loss, medical, etc.) |
| asks_time         | Borrower asking for more time before paying |

## Important Rules

- Spec Invariant I5: Every borrower message must be correctly classified
- If a borrower clearly says "I can't pay, I lost my job" → should be "hardship", NOT "unclear"
- If a borrower says "I want to settle" → should be "wants_settlement", NOT "unclear"
- If a borrower says "this debt is wrong" or "I don't owe this" → should be "disputes"
- If a borrower says "stop messaging me" → this is also a DNC signal (compliance issue beyond classification)
- "asks_time" is for explicit time requests ("give me a week", "I'll pay next month")
- Messages that are genuinely ambiguous CAN be "unclear" — not every "unclear" is wrong
- Hindi/Hinglish messages should be interpreted correctly

## Rubric (1–3 Scale)

| Score | Label     | Meaning |
|-------|-----------|---------|
| 1     | Correct   | Classification matches the borrower's expressed intent |
| 2     | Debatable | Classification is plausible but another label fits better. The error is unlikely to cause harm but represents a misread. |
| 3     | Wrong     | Classification clearly misses the borrower's actual intent. This could lead to wrong agent behavior. |

## Borrower Messages & Bot Classifications

{classifications_text}

## Instructions

For each classified borrower message:
1. Read the borrower's actual text carefully (including Hindi/Hinglish)
2. Determine what the correct classification should be
3. Compare with the bot's classification
4. Score accuracy using the rubric

Only report entries where score >= 2 (i.e., where classification is debatable or wrong).

Respond in this exact JSON format:
{{
  "turn_evaluations": [
    {{
      "turn": <int>,
      "borrower_text": "<text>",
      "bot_classification": "<what bot assigned>",
      "correct_classification": "<what you think it should be>",
      "accuracy_score": <1-3>,
      "reasoning": "<why the bot's classification is wrong or debatable>"
    }}
  ],
  "overall_accuracy_score": <1-3>,
  "misclassification_rate": <float 0-1>,
  "summary": "<assessment of classification quality>"
}}

If all classifications are correct, return:
{{
  "turn_evaluations": [],
  "overall_accuracy_score": 1,
  "misclassification_rate": 0.0,
  "summary": "All classifications are accurate."
}}"""
