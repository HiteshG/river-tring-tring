"""
Prompt Templates Package
=========================
All LLM prompt templates stored centrally for easy reference and modification.

Modules:
  - compliance_prompt: Section 8 compliance evaluation (1-5 rubric)
  - quality_prompt: Section 10 quality assessment (1-3 rubric)
  - classification_prompt: Invariant I5 classification accuracy (1-3 rubric)
  - combined_prompt: All three merged into one prompt
"""

from prompts.compliance_prompt import COMPLIANCE_PROMPT_TEMPLATE
from prompts.quality_prompt import QUALITY_PROMPT_TEMPLATE
from prompts.classification_prompt import CLASSIFICATION_PROMPT_TEMPLATE
from prompts.combined_prompt import COMBINED_PROMPT_TEMPLATE

__all__ = [
    "COMPLIANCE_PROMPT_TEMPLATE",
    "QUALITY_PROMPT_TEMPLATE",
    "CLASSIFICATION_PROMPT_TEMPLATE",
    "COMBINED_PROMPT_TEMPLATE",
]
