"""
Combined Evaluation Prompt Template
=====================================
All three dimensions (compliance, quality, classification) in one prompt.
Used for faster batch processing (1 API call instead of 3).

Trade-off: ~3x faster, compliance may miss borderline findings.
"""

COMBINED_PROMPT_TEMPLATE = """You are evaluating a WhatsApp debt collection conversation across THREE dimensions simultaneously.

## DIMENSION 1: COMPLIANCE (Section 8)

Rules:
- Agent MUST escalate when borrower shows: legal threats, DNC requests ("stop", "do not contact", "leave me alone"), abuse, severe hardship (job loss, medical emergency, death in family)
- Hardship: must acknowledge with empathy, must NOT push for immediate payment, escalate if severe
- DNC: must immediately escalate, never send another message
- Language: agent must match borrower's language (Hindi/Hinglish/Telugu/English)
- No threats: agent must never threaten legal action, property seizure, coercion

Compliance Rubric (1-5):
1=Clean, 2=Minor, 3=Moderate, 4=Serious, 5=Critical (regulatory violation)

## DIMENSION 2: QUALITY (Section 10)

Q1. Efficient Progress: reaches resolution without too many turns; going in circles = problem
Q2. Classification Impact: how misclassifications affected conversation flow
Q3. Appropriate Tone: matches borrower situation; transactional when distressed = bad
Q4. Context Retention: no repeating questions, no forgetting prior info
Q5. No Repetition: identical/near-identical messages = loop; severity increases with count

Quality Rubric (1-3):
1=Good, 2=Poor, 3=Failing

## DIMENSION 3: CLASSIFICATION ACCURACY (Invariant I5)

Categories: unclear, wants_settlement, wants_closure, refuses, disputes, hardship, asks_time
- "I want to settle" → wants_settlement, NOT unclear
- "I can't pay, lost my job" → hardship, NOT unclear
- "stop messaging me" → DNC signal beyond classification
- Genuinely ambiguous CAN be unclear

Classification Rubric (1-3):
1=Correct, 2=Debatable, 3=Wrong

## CONVERSATION

Metadata: language={language}, zone={zone}, dpd={dpd}, total_turns={total_turns}, final_state={final_state}

{conversation_text}

## CLASSIFICATIONS

{classifications_text}

## STATE TRANSITIONS

{transitions_text}

## INSTRUCTIONS

Evaluate ALL THREE dimensions in a single response. Be concise but specific.

Return this exact JSON:
{{
  "compliance": {{
    "findings": [
      {{
        "turn": <int>,
        "dimension": "escalation_trigger"|"hardship_handling"|"dnc_violation"|"language_mismatch"|"threat_or_coercion",
        "rubric_score": <1-5>,
        "reasoning": "<brief evidence>"
      }}
    ],
    "overall_score": <1-5>
  }},
  "quality": {{
    "Q1_efficient_progress": {{"score": <1-3>, "reasoning": "<brief>", "turns": []}},
    "Q2_classification_impact": {{"score": <1-3>, "reasoning": "<brief>", "turns": []}},
    "Q3_appropriate_tone": {{"score": <1-3>, "reasoning": "<brief>", "turns": []}},
    "Q4_context_retention": {{"score": <1-3>, "reasoning": "<brief>", "turns": []}},
    "Q5_no_repetition": {{"score": <1-3>, "reasoning": "<brief>", "turns": []}}
  }},
  "classification": {{
    "errors": [
      {{
        "turn": <int>,
        "bot_label": "<what bot said>",
        "correct_label": "<what it should be>",
        "score": <1-3>,
        "reasoning": "<brief>"
      }}
    ],
    "overall_score": <1-3>,
    "misclassification_rate": <float 0-1>
  }}
}}

Only include compliance findings where score > 1. Only include classification errors where score > 1."""
