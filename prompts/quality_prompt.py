"""
Quality Evaluation Prompt Template
====================================
Section 10 — Communication quality expectations.
Rubric: 1-3 scale (Good → Failing).

Used by: QualityEvaluator (separate mode), CombinedLLMEvaluator (embedded)
"""

QUALITY_PROMPT_TEMPLATE = """You are evaluating the communication quality of a WhatsApp debt collection agent.

## Spec Rules (Section 10 — Quality Expectations)

These are NOT hard rules — they are expectations for a good conversation. Violations lower quality but don't break the spec.

Q1. Efficient Progress: A good conversation reaches payment_confirmed or an appropriate exit state without too many turns. Conversations that go in circles without making progress have a quality problem.

Q2. Accurate Classification: The agent's classification of the borrower's intent should match what the borrower actually said. Repeatedly classifying clear messages as "unclear" is a sign of a classification problem. (Note: classification accuracy is checked separately — focus here on how misclassifications affected conversation flow.)

Q3. Appropriate Tone: The agent's tone should match the situation:
- Being transactional/cold when the borrower is in distress → bad
- Being aggressive with a cooperative borrower → bad  
- Being empathetic and warm with a cooperative borrower → good
- Severity depends on context.

Q4. Remembering Context: The agent should not repeat itself, re-ask questions it already asked, or forget what was said earlier. Examples:
- Asking for identity verification after already completing it
- Re-explaining settlement options already discussed
- Forgetting the borrower's stated preference

Q5. No Repetition: The agent should not send identical or near-identical messages. Repeated messages suggest the agent is stuck in a loop. Severity INCREASES with the number of repetitions:
- 2 repeats: moderate issue
- 3+ repeats: severe quality failure
- 5+ repeats: conversation is broken

## Rubric (1–3 Scale)

| Score | Label   | Meaning |
|-------|---------|---------|
| 1     | Good    | Meets or exceeds expectations for this dimension. No issues. |
| 2     | Poor    | Noticeable quality gap that affects borrower experience. Something went wrong but conversation may still function. |
| 3     | Failing | Severe quality failure. Conversation is ineffective, frustrating, or harmful to the borrower. |

## Conversation

Total turns: {total_turns} | Final state: {final_state} | Language: {language}

{conversation_text}

## Instructions

Evaluate each quality dimension (Q1-Q5). For each dimension:
1. Assess the quality level using the rubric
2. Identify specific turns where issues occurred
3. Explain your reasoning with evidence from the conversation

Focus especially on:
- Repetition loops (exact or near-identical bot messages)
- Conversations that fail to make progress
- Tone mismatches between borrower emotional state and agent response

Respond in this exact JSON format:
{{
  "dimensions": {{
    "Q1_efficient_progress": {{
      "score": <1-3>,
      "reasoning": "<specific evidence>",
      "problem_turns": [<turn numbers>]
    }},
    "Q2_classification_impact": {{
      "score": <1-3>,
      "reasoning": "<how misclassifications affected flow>",
      "problem_turns": [<turn numbers>]
    }},
    "Q3_appropriate_tone": {{
      "score": <1-3>,
      "reasoning": "<specific evidence>",
      "problem_turns": [<turn numbers>]
    }},
    "Q4_context_retention": {{
      "score": <1-3>,
      "reasoning": "<specific evidence>",
      "problem_turns": [<turn numbers>]
    }},
    "Q5_no_repetition": {{
      "score": <1-3>,
      "reasoning": "<specific evidence with count of repeated messages>",
      "problem_turns": [<turn numbers>]
    }}
  }},
  "overall_quality_score": <1-3>,
  "summary": "<1-2 sentence quality assessment>"
}}"""
