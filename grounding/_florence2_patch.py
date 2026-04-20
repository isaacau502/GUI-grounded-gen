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

    # --- Patch 2: configuration_florence2.py — add class-level default
    # for forced_bos_token_id so direct self.forced_bos_token_id access works
    # in newer transformers where PretrainedConfig no longer sets it.
    MARKER_CFG = "# florence2-patch: forced_bos_token_id default"
    for root in cache_roots:
        if not root or not os.path.isdir(root):
            continue
        for cf in glob.glob(f"{root}/**/configuration_florence2.py", recursive=True):
            if cf in seen:
                continue
            seen.add(cf)
            try:
                with open(cf) as f:
                    src = f.read()
            except Exception:
                continue
            if MARKER_CFG in src:
                continue
            new_src = src
            import re
            for cls in ("Florence2LanguageConfig", "Florence2Config",
                        "Florence2VisionConfig"):
                pat = re.compile(
                    rf"^(class\s+{cls}\s*\([^)]*\)\s*:\s*\n)",
                    re.MULTILINE,
                )
                def repl(m):
                    return m.group(1) + (
                        f"    forced_bos_token_id = None  {MARKER_CFG}\n"
                    )
                new_src = pat.sub(repl, new_src, count=1)
            if new_src != src:
                try:
                    with open(cf, "w") as f:
                        f.write(new_src)
                    patched += 1
                    if verbose:
                        print(f"[florence2-patch] fixed config-source {cf}")
                except Exception as e:
                    if verbose:
                        print(f"[florence2-patch] write failed {cf}: {e}")

    # --- Patch 2b: modeling_florence2.py — add _supports_sdpa + related
    # class attributes that newer transformers expects on PreTrainedModel
    # subclasses but older Florence-2 remote code doesn't set.
    MARKER_MODEL = "# florence2-patch: modern transformers attrs"
    for root in cache_roots:
        if not root or not os.path.isdir(root):
            continue
        for cf in glob.glob(f"{root}/**/modeling_florence2.py", recursive=True):
            if cf in seen:
                continue
            seen.add(cf)
            try:
                with open(cf) as f:
                    src = f.read()
            except Exception:
                continue
            if MARKER_MODEL in src:
                continue
            new_src = src
            import re
            # Patch every Florence2*PreTrainedModel / ForConditionalGeneration
            # class with safe defaults for SDPA/flash attn attributes.
            for cls in (
                "Florence2PreTrainedModel",
                "Florence2ForConditionalGeneration",
                "Florence2LanguagePreTrainedModel",
                "Florence2LanguageForConditionalGeneration",
                "Florence2VisionModel",
            ):
                pat = re.compile(
                    rf"^(class\s+{cls}\s*\([^)]*\)\s*:\s*\n)",
                    re.MULTILINE,
                )
                def repl(m):
                    return m.group(1) + (
                        f"    _supports_sdpa = True  {MARKER_MODEL}\n"
                        f"    _supports_flash_attn_2 = False  {MARKER_MODEL}\n"
                        f"    _supports_cache_class = False  {MARKER_MODEL}\n"
                    )
                new_src = pat.sub(repl, new_src, count=1)
            if new_src != src:
                try:
                    with open(cf, "w") as f:
                        f.write(new_src)
                    patched += 1
                    if verbose:
                        print(f"[florence2-patch] fixed modeling-source {cf}")
                except Exception as e:
                    if verbose:
                        print(f"[florence2-patch] write failed {cf}: {e}")

    # --- Patch 3: processing_florence2.py — replace deprecated
    # `tokenizer.additional_special_tokens` with getattr fallback that works
    # on modern transformers (where the attribute was removed from tokenizer).
    MARKER_PROC = "# florence2-patch: additional_special_tokens fallback"
    for root in cache_roots:
        if not root or not os.path.isdir(root):
            continue
        for cf in glob.glob(f"{root}/**/processing_florence2.py", recursive=True):
            if cf in seen:
                continue
            seen.add(cf)
            try:
                with open(cf) as f:
                    src = f.read()
            except Exception:
                continue
            if MARKER_PROC in src:
                continue

            # Replace with an expression that works on both old and new
            # transformers. Keep it a single expression — no multi-line
            # comments — so surrounding `+ \` line-continuations stay intact.
            # Marker added via trailing `# ...` on same line.
            new_src = src.replace(
                "tokenizer.additional_special_tokens",
                f"(getattr(tokenizer, 'additional_special_tokens', None) or [])",
            )
            # Also track that we've patched this file
            if new_src != src:
                new_src = f"{MARKER_PROC}\n" + new_src

            if new_src != src:
                try:
                    with open(cf, "w") as f:
                        f.write(new_src)
                    patched += 1
                    if verbose:
                        print(f"[florence2-patch] fixed processing-source {cf}")
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


_KNOWN_ATTRS = (
    "forced_bos_token_id",
    "additional_special_tokens",
    "_supports_sdpa",
    "_supports_flash_attn_2",
    "_supports_cache_class",
)


def _is_known_attr_error(e: Exception) -> bool:
    msg = str(e)
    return isinstance(e, AttributeError) and any(k in msg for k in _KNOWN_ATTRS)


def load_florence2_processor_safe(florence_base: str = "microsoft/Florence-2-base"):
    """Load Florence-2 processor with automatic bug workaround.

    Florence-2's remote code (`trust_remote_code=True`) was written against
    old transformers APIs and breaks on modern versions. We patch the cached
    source files on demand and retry.
    """
    from transformers import AutoProcessor

    for attempt in range(3):  # up to 3 retries; different bugs may chain
        try:
            return AutoProcessor.from_pretrained(florence_base, trust_remote_code=True)
        except Exception as e:
            if not _is_known_attr_error(e):
                raise
            print(f"[florence2-patch] attempt {attempt+1}: hit '{e}', patching...")
            patch_florence2_cache(verbose=True)
            _clear_florence2_modules()
    raise RuntimeError(
        "Failed to load Florence-2 processor after 3 patch attempts. "
        "Transformers version may be too new for Florence-2's remote code."
    )


def load_florence2_model_safe(
    florence_base: str = "microsoft/Florence-2-base",
    torch_dtype=None,
):
    """Load Florence-2 model with the same bug workaround.

    Args:
        torch_dtype: if provided (e.g. torch.float16), model loads directly
            in that dtype. Recommended for OmniParser which ships fp16
            safetensors — loading in fp16 from the start avoids the mixed
            fp16/fp32 state_dict overlay problem.
    """
    from transformers import AutoModelForCausalLM

    kwargs = {"trust_remote_code": True}
    if torch_dtype is not None:
        kwargs["torch_dtype"] = torch_dtype

    for attempt in range(3):
        try:
            return AutoModelForCausalLM.from_pretrained(florence_base, **kwargs)
        except Exception as e:
            if not _is_known_attr_error(e):
                raise
            print(f"[florence2-patch] model attempt {attempt+1}: '{e}', patching...")
            patch_florence2_cache(verbose=True)
            _clear_florence2_modules()
    raise RuntimeError("Failed to load Florence-2 model after 3 patch attempts.")
