"""JEDI-side query templates.

For Qwen72B repair-prompt variants (pixel / normalized / quadrant — the 1h
A/B on Day 1), see pipeline/prompts.py.
"""

CLICK_ELEMENT = (
    "Click the element with {issue_type}. "
    "Output only: pyautogui.click(x=<int>, y=<int>)"
)


def format_query(template: str, **kwargs) -> str:
    return template.format(**kwargs)
