"""JEDI-7B wrapper for visual UI element grounding.

Lazy-imports torch/vllm/qwen_vl_utils so this module is safe to import on
machines without a GPU (Mac dev, CI). Heavy deps only load when JEDI is
instantiated or query() is called.

Usage:
    from grounding.jedi import JEDI
    from grounding.prompts import CLICK_ELEMENT, format_query

    jedi = JEDI()  # loads weights (~30s on A100 with Drive cache)
    q = format_query(CLICK_ELEMENT, issue_type="a button labeled 'Sign up'")
    result = jedi.query("/content/drive/MyDrive/samples/1.png", q)
    # result -> {'point': (x, y) | None, 'raw_output': str,
    #           'parse_success': bool, 'original_size': (w, h),
    #           'resized_size': (w, h)}
"""

import base64
import io
import re


_PARSE_PATTERNS = [
    r'x\s*=\s*([\d.]+)\s*,?\s*y\s*=\s*([\d.]+)',
    r'pyautogui\.click\(\s*x\s*=\s*([\d.]+)\s*,\s*y\s*=\s*([\d.]+)',
    r'\[(\d+)\s*,\s*(\d+)\]',
    r'\((\d+)\s*,\s*(\d+)\)',
]


class JEDI:
    def __init__(
        self,
        model_path: str = "xlangai/Jedi-7B-1080p",
        dtype: str = "auto",
        gpu_memory_utilization: float = 0.9,
        max_model_len: int = 8192,
    ):
        import torch
        from vllm import LLM

        if dtype == "auto":
            gpu = torch.cuda.get_device_name(0)
            dtype = "bfloat16" if ("A100" in gpu or "H100" in gpu) else "float16"

        self.llm = LLM(
            model=model_path,
            dtype=dtype,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            limit_mm_per_prompt={"image": 1},
        )

    def query(self, image_path: str, instruction: str) -> dict:
        from PIL import Image
        from qwen_vl_utils import smart_resize
        from vllm import SamplingParams

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        resized_h, resized_w = smart_resize(
            orig_h, orig_w, factor=28,
            min_pixels=256 * 28 * 28, max_pixels=1280 * 28 * 28,
        )
        img_resized = img.resize((resized_w, resized_h))

        buf = io.BytesIO()
        img_resized.save(buf, format="PNG")
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": instruction},
            ],
        }]
        outputs = self.llm.chat(
            messages,
            sampling_params=SamplingParams(temperature=0.0, max_tokens=64),
        )
        raw = outputs[0].outputs[0].text

        point = _parse_and_rescale(raw, orig_w, orig_h, resized_w, resized_h)
        return {
            "point": point,
            "raw_output": raw,
            "parse_success": point is not None,
            "original_size": (orig_w, orig_h),
            "resized_size": (resized_w, resized_h),
        }


def _parse_and_rescale(raw, orig_w, orig_h, resized_w, resized_h):
    for pat in _PARSE_PATTERNS:
        m = re.search(pat, raw)
        if m:
            cx_r = float(m.group(1))
            cy_r = float(m.group(2))
            return (
                int(cx_r * orig_w / resized_w),
                int(cy_r * orig_h / resized_h),
            )
    return None
