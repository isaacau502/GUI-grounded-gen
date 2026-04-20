"""Plumbing test for run_repair_grounded.py monkeypatch.

Creates a fake grounding cache with a known sentinel, imports the grounded
runner (which applies the monkeypatches), then manually calls the patched
get_design_repair_prompt and asserts the sentinel appears in the output.

Run: python scripts/_plumbing_test.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Write a fake cache.
fake = {
    "react/1": {
        "prompt_block": "<<<GROUNDING-SENTINEL-12345>>>",
        "num_elements": 7,
    },
}
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
json.dump(fake, tmp)
tmp.close()
os.environ["GROUNDING_CACHE"] = tmp.name

# Import the grounded runner to apply monkeypatches.
sys.path.insert(0, str(REPO / "scripts"))
import run_repair_grounded  # noqa: F401 — applies patches on import

# Now verify: set TLS to "react/1", call the patched prompt fn, expect sentinel.
from utils import Framework, Mode  # type: ignore
from prompt.repair_prompt import get_design_repair_prompt  # type: ignore

run_repair_grounded._set_current("react", 1)

system_prompt, prompt = get_design_repair_prompt(
    output_framework=Framework.REACT,
    mode=Mode.BOTH,
    code="<div>placeholder</div>",
)

assert "<<<GROUNDING-SENTINEL-12345>>>" in prompt, (
    "FAIL: grounding sentinel not in prompt. Monkeypatch broken."
)
print("PASS: grounding sentinel appears in prompt.")
print(f"Prompt length: {len(prompt)} chars")
print(f"System prompt length: {len(system_prompt)} chars")
print(f"\nLast 400 chars of prompt:\n---")
print(prompt[-400:])
