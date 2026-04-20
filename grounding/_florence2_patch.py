"""Workaround for Florence-2 remote-code bug.

When loading microsoft/Florence-2-base via AutoProcessor with
trust_remote_code=True, the downloaded processing_florence2.py references
config.text_config.forced_bos_token_id, which is not set in the cached
config.json. This raises:

    AttributeError: 'Florence2LanguageConfig' object has no attribute
                    'forced_bos_token_id'

This module patches the cached config.json to add the missing attribute.
Safe to call multiple times (no-op if already patched or files not cached yet).
"""

import glob
import json
import os


def patch_florence2_cache(verbose: bool = True) -> int:
    """Scan HF cache for Florence-2 configs and add forced_bos_token_id if missing.

    Returns the number of files patched.
    """
    cache_roots = [
        os.path.expanduser("~/.cache/huggingface/hub"),
        os.environ.get("HF_HOME", ""),
        os.environ.get("TRANSFORMERS_CACHE", ""),
    ]
    seen = set()
    patched = 0

    for root in cache_roots:
        if not root or not os.path.isdir(root):
            continue
        # Florence-2 cached config lives at:
        # ~/.cache/huggingface/hub/models--microsoft--Florence-2-*/snapshots/<hash>/config.json
        for pattern in [
            f"{root}/models--microsoft--Florence-2*/snapshots/*/config.json",
            f"{root}/**/Florence-2*/config.json",
        ]:
            for cf in glob.glob(pattern, recursive=True):
                if cf in seen:
                    continue
                seen.add(cf)
                try:
                    with open(cf) as f:
                        cfg = json.load(f)
                except Exception:
                    continue

                modified = False

                # Patch 1: text_config.forced_bos_token_id
                if "text_config" in cfg and isinstance(cfg["text_config"], dict):
                    if "forced_bos_token_id" not in cfg["text_config"]:
                        cfg["text_config"]["forced_bos_token_id"] = None
                        modified = True

                # Patch 2: root-level (belt and suspenders)
                if "forced_bos_token_id" not in cfg:
                    cfg["forced_bos_token_id"] = None
                    modified = True

                if modified:
                    try:
                        with open(cf, "w") as f:
                            json.dump(cfg, f, indent=2)
                        patched += 1
                        if verbose:
                            print(f"[florence2-patch] fixed {cf}")
                    except Exception as e:
                        if verbose:
                            print(f"[florence2-patch] failed to write {cf}: {e}")

    return patched


def load_florence2_processor_safe(florence_base: str = "microsoft/Florence-2-base"):
    """Load Florence-2 processor with automatic bug workaround.

    Tries normally first. On the known AttributeError, patches the cache
    and retries once.
    """
    from transformers import AutoProcessor

    try:
        return AutoProcessor.from_pretrained(florence_base, trust_remote_code=True)
    except AttributeError as e:
        if "forced_bos_token_id" not in str(e):
            raise
        print(f"[florence2-patch] Hit forced_bos_token_id bug, patching cache...")
        n = patch_florence2_cache(verbose=True)
        if n == 0:
            print(
                f"[florence2-patch] No files patched. "
                f"The processor may not be cached yet."
            )
        return AutoProcessor.from_pretrained(florence_base, trust_remote_code=True)


def load_florence2_model_safe(florence_base: str = "microsoft/Florence-2-base"):
    """Load Florence-2 model with the same bug workaround."""
    from transformers import AutoModelForCausalLM

    try:
        return AutoModelForCausalLM.from_pretrained(
            florence_base, trust_remote_code=True
        )
    except AttributeError as e:
        if "forced_bos_token_id" not in str(e):
            raise
        print(f"[florence2-patch] Hit forced_bos_token_id bug, patching cache...")
        patch_florence2_cache(verbose=True)
        return AutoModelForCausalLM.from_pretrained(
            florence_base, trust_remote_code=True
        )
