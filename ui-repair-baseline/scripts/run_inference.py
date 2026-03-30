import sys
import os
import json
import argparse
import time
import traceback

import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

from designbench_utils import Framework, Mode, get_design_repair_prompt, extract_repair_content

# --- Constants ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(SCRIPT_DIR, "../../external/DesignBench/data/DesignRepair")
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "../results")

FRAMEWORK_RANGES = {
    Framework.VANILLA: range(1, 29),   # 28 samples
    Framework.REACT:   range(1, 29),   # 28 samples
    Framework.VUE:     range(1, 28),   # 27 samples
    Framework.ANGULAR: range(1, 29),   # 28 samples
}

FORMAT_MAP = {
    Framework.VANILLA: ["html"],
    Framework.REACT:   ["jsx"],
    Framework.VUE:     ["vue"],
    Framework.ANGULAR: ["ts", "angular"],
}


# --- Model ---

def load_model(model_id):
    print(f"Loading model: {model_id}")
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(
        model_id,
        max_pixels=1024 * 28 * 28,
    )
    print("Model loaded.")
    return model, processor


# --- Data loading ---

def load_sample(data_dir, framework, number):
    sample_dir = os.path.join(data_dir, framework.value, str(number))
    config_path = os.path.join(sample_dir, f"{number}.json")
    image_path = os.path.join(sample_dir, f"{number}.png")

    with open(config_path, "r") as f:
        config = json.load(f)

    if framework == Framework.REACT:
        code = config["component_jsx"]
    else:
        code = config["code"]

    return code, image_path


# --- Prompt construction ---

def build_messages(framework, code, image_path):
    system_prompt, user_prompt = get_design_repair_prompt(
        output_framework=framework,
        mode=Mode.BOTH,
        code=code,
    )

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": [
            {"type": "text", "text": user_prompt},
            {"type": "image", "image": f"file://{os.path.abspath(image_path)}"},
        ]},
    ]
    return messages


# --- Inference ---

def run_single_inference(model, processor, messages, max_new_tokens=8192):
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)

    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.0,
            do_sample=False,
        )

    generated_ids = output_ids[:, inputs.input_ids.shape[1]:]
    response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response.strip()


# --- Saving ---

def get_model_name(model_id):
    return model_id.split("/")[-1]


def get_save_dir(output_dir, framework, model_name):
    fw = framework.value
    return os.path.join(output_dir, f"{fw}-{fw}", model_name)


def is_sample_done(output_dir, framework, number, model_name):
    fw = framework.value
    save_dir = get_save_dir(output_dir, framework, model_name)
    base_name = f"{fw}_{number}_{model_name}_{fw}_both"
    return os.path.exists(os.path.join(save_dir, f"{base_name}.json"))


def parse_and_save(response, output_dir, framework, number, model_name):
    issues, reasoning, code = extract_repair_content(response, framework)

    fw = framework.value
    save_dir = get_save_dir(output_dir, framework, model_name)
    os.makedirs(save_dir, exist_ok=True)
    base_name = f"{fw}_{number}_{model_name}_{fw}_both"

    # Save JSON metadata
    if framework == Framework.ANGULAR and isinstance(code, tuple) and len(code) == 2:
        code_json = {"ts": code[0], "html": code[1]}
    elif isinstance(code, tuple) and len(code) == 1:
        code_json = code[0]
    elif isinstance(code, tuple):
        code_json = list(code)
    else:
        code_json = code

    result = {
        "Issues": issues if isinstance(issues, list) else [],
        "Reasoning": reasoning,
        "Code": code_json,
    }

    with open(os.path.join(save_dir, f"{base_name}.json"), "w") as f:
        json.dump(result, f, indent=4)

    # Save raw response
    with open(os.path.join(save_dir, f"{base_name}.txt"), "w") as f:
        f.write(response)

    # Save code files
    formats = FORMAT_MAP[framework]
    if framework == Framework.ANGULAR and isinstance(code, tuple) and len(code) == 2:
        code_contents = [code[0], code[1]]  # ts, angular(html)
    elif isinstance(code, tuple):
        code_contents = list(code)
    elif isinstance(code, str):
        code_contents = [code]
    else:
        code_contents = []

    for content, fmt in zip(code_contents, formats):
        with open(os.path.join(save_dir, f"{base_name}.{fmt}"), "w") as f:
            f.write(content if content else "")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Run Qwen2.5-VL-7B repair inference on DesignBench")
    parser.add_argument("--data-dir", type=str, default=DEFAULT_DATA_DIR,
                        help="Path to DesignRepair data directory")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
                        help="Path to save results")
    parser.add_argument("--model-id", type=str, default="Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
                        help="HuggingFace model ID")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max samples to process (for testing)")
    parser.add_argument("--frameworks", nargs="+", default=["vanilla", "react", "vue", "angular"],
                        help="Frameworks to process")
    parser.add_argument("--max-new-tokens", type=int, default=8192,
                        help="Max tokens to generate per sample")
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    output_dir = os.path.abspath(args.output_dir)
    model_name = get_model_name(args.model_id)

    # Build sample list
    samples = []
    for fw_name in args.frameworks:
        fw = Framework(fw_name)
        for num in FRAMEWORK_RANGES[fw]:
            samples.append((fw, num))

    if args.limit:
        samples = samples[:args.limit]

    # Filter already completed
    pending = [(fw, num) for fw, num in samples if not is_sample_done(output_dir, fw, num, model_name)]

    print(f"Total: {len(samples)}, Done: {len(samples) - len(pending)}, Pending: {len(pending)}")

    if not pending:
        print("All samples already completed.")
        return

    # Load model
    model, processor = load_model(args.model_id)

    # Process samples
    success = 0
    failed = 0

    for i, (framework, number) in enumerate(pending):
        print(f"[{i+1}/{len(pending)}] {framework.value}/{number}...", end=" ", flush=True)
        start = time.time()

        try:
            code, image_path = load_sample(data_dir, framework, number)
            messages = build_messages(framework, code, image_path)
            response = run_single_inference(model, processor, messages, max_new_tokens=args.max_new_tokens)
            parse_and_save(response, output_dir, framework, number, model_name)

            elapsed = time.time() - start
            print(f"OK ({elapsed:.1f}s)")
            success += 1
        except Exception as e:
            elapsed = time.time() - start
            print(f"FAILED ({elapsed:.1f}s): {e}")
            traceback.print_exc()
            failed += 1

    print(f"\nDone. Success: {success}, Failed: {failed}")


if __name__ == "__main__":
    main()
