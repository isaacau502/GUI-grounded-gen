"""GUI grounding models for UI defect localization.

Wraps grounding models (JEDI-7B primary, OmniParser as alternative) to produce
structured visual annotations over a rendered UI screenshot.
"""
from grounding.jedi import JEDI
from grounding.prompts import CLICK_ELEMENT, format_query

__all__ = ["JEDI", "CLICK_ELEMENT", "format_query"]
