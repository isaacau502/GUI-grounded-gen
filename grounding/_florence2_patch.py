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
    """Scan HF cache for Florence-2 configs + code and fix forced_bos_token_id.

    Patches both:
      1. config.json files: add forced_bos_token_id = None at text_config + root
      2. configuration_florence2.py: add class attribute default on
         Florence2LanguageConfig so direct attribute access works

    Returns total number of files patched.
    """
    cache_roots = [
        os.path.expanduser("~/.cache/huggingface/hub"),
        os.path.expanduser("~/.cache/huggingface/modules"),
        os.environ.get("HF_HOME", ""),
        os.environ.get("TRANSFORMERS_CACHE", ""),
    ]
    seen = set()
    patched = 0

    # --- Patch 1: config.json files ---
    for root in cache_roots:
        if not root or not os.path.isdir(root):
            continue
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
                if "text_config" in cfg and isinstance(cfg["text_config"], dict):
                    if "forced_bos_token_id" not in cfg["text_config"]:
                        cfg["text_config"]["forced_bos_token_id"] = None
                        modified = True
                if "forced_bos_token_id" not in cfg:
                    cfg["forced_bos_token_id"] = None
                    modified = True

                if modified:
                    try:
                        with open(cf, "w") as f:
                            json.dump(cfg, f, indent=2)
                        patched += 1
                        if verbose:
                            print(f"[florence2-patch] fixed config {cf}")
                    except Exception as e:
                        if verbose:
                            print(f"[florence2-patch] write failed {cf}: {e}")

    # --- Patch 2: configuration_florence2.py source code ---
    # Add forced_bos_token_id class attribute to Florence2LanguageConfig
    # (and Florence2Config for good measure), so attribute access doesn't fail
    # when the config is being built from kwargs.
    MARKER = "# florence2-patch: forced_bos_token_id default"
    for root in cache_roots:
        if not root or not os.path.isdir(root):
            continue
        for pattern in [
            f"{root}/**/configuration_florence2.py",
        ]:
            for cf in glob.glob(pattern, recursive=True):
                if cf in seen:
                    continue
                seen.add(cf)
                try:
                    with open(cf) as f:
                        src = f.read()
                except Exception:
                    continue

                if MARKER in src:
                    continue  # already patched

                # Strategy: insert class-level default right after each
                # `class Florence2LanguageConfig(...):` or `class Florence2Config(...):`
                # We insert a line that sets the attr on the class.
                new_src = src
                for cls in ("Florence2LanguageConfig", "Florence2Config",
                            "Florence2VisionConfig"):
                    # Find class definition
                    import re
                    pat = re.compile(
                        rf"^(class\s+{cls}\s*\([^)]*\)\s*:\s*\n)",
                        re.MULTILINE,
                    )
                    # Insert MARKER line right after class declaration
                    def repl(m):
                        return m.group(1) + (
                            f"    forced_bos_token_id = None  {MARKER}\n"
                        )
                    new_src = pat.sub(repl, new_src, count=1)

                if new_src != src:
                    try:
                        with open(cf, "w") as f:
                            f.write(new_src)
                        patched += 1
                        if verbose:
                            print(f"[florence2-patch] fixed source {cf}")
                    except Exception as e:
                        if verbose:
                            print(f"[florence2-patch] write failed {cf}: {e}")

    return patched


def _clear_florence2_modules():
    """Remove cached transformers_modules.Florence-2* entries from sys.modules
    so the patched source is re-loaded on next import."""
    import sys
    to_del = [k for k in list(sys.modules.keys())
              if "florence" in k.lower() or "Florence" in k]
    for k in to_del:
        del sys.modules[k]


def load_florence2_processor_safe(florence_base: str = "microsoft/Florence-2-base"):
    """Load Florence-2 processor with automatic bug workaround.

    Tries normally first. On the known AttributeError, patches the cache
    AND purges cached modules, then retries once.
    """
    from transformers import AutoProcessor

    try:
        return AutoProcessor.from_pretrained(florence_base, trust_remote_code=True)
    except AttributeError as e:
        if "forced_bos_token_id" not in str(e):
            raise
        print(f"[florence2-patch] Hit forced_bos_token_id bug, patching...")
        n = patch_florence2_cache(verbose=True)
        if n == 0:
            print(
                f"[florence2-patch] No files patched. "
                f"The processor may not be cached yet."
            )
        _clear_florence2_modules()
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
        print(f"[florence2-patch] Hit forced_bos_token_id bug, patching...")
        patch_florence2_cache(verbose=True)
        _clear_florence2_modules()
        return AutoModelForCausalLM.from_pretrained(
            florence_base, trust_remote_code=True
        )
