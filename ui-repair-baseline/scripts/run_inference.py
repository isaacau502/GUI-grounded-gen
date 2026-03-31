import sys
import os
import json
import base64
import argparse
import time
import traceback

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from designbench_utils import Framework, Mode, get_design_repair_prompt, extract_repair_content

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


def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


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


def build_api_messages(framework, code, image_path):
    system_prompt, user_prompt = get_design_repair_prompt(
        output_framework=framework,
        mode=Mode.BOTH,
        code=code,
    )

    image_b64 = encode_image(image_path)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{image_b64}",
                "detail": "high",
            }},
        ]},
    ]
    return messages


def run_api_inference(client, model_name, messages, max_tokens=8192):
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0,
        seed=42,
        stream=True,
    )

    full_response = ""
    for chunk in response:
        if chunk.choices and hasattr(chunk.choices[0], "delta"):
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_response += delta.content
    return full_response.strip()


def get_model_short_name(model_name):
    return model_name.replace("/", "-")


def get_save_dir(output_dir, framework, model_short):
    fw = framework.value
    return os.path.join(output_dir, f"{fw}-{fw}", model_short)


def is_sample_done(output_dir, framework, number, model_short):
    fw = framework.value
    save_dir = get_save_dir(output_dir, framework, model_short)
    base_name = f"{fw}_{number}_{model_short}_{fw}_both"
    return os.path.exists(os.path.join(save_dir, f"{base_name}.json"))


def parse_and_save(response, output_dir, framework, number, model_short):
    issues, reasoning, code = extract_repair_content(response, framework)

    fw = framework.value
    save_dir = get_save_dir(output_dir, framework, model_short)
    os.makedirs(save_dir, exist_ok=True)
    base_name = f"{fw}_{number}_{model_short}_{fw}_both"

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
        code_contents = [code[0], code[1]]
    elif isinstance(code, tuple):
        code_contents = list(code)
    elif isinstance(code, str):
        code_contents = [code]
    else:
        code_contents = []

    for content, fmt in zip(code_contents, formats):
        with open(os.path.join(save_dir, f"{base_name}.{fmt}"), "w") as f:
            f.write(content if content else "")


def main():
    parser = argparse.ArgumentParser(description="Run Qwen VL repair inference on DesignBench via API")
    parser.add_argument("--data-dir", type=str, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", type=str, default="qwen2.5-vl-7b-instruct",
                        help="Qwen model name")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--frameworks", nargs="+", default=["vanilla", "react", "vue", "angular"])
    parser.add_argument("--max-tokens", type=int, default=8192)
    args = parser.parse_args()

    api_key = os.environ.get("QWEN_API_KEY")
    if not api_key:
        print("Error: QWEN_API_KEY environment variable not set")
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )

    data_dir = os.path.abspath(args.data_dir)
    output_dir = os.path.abspath(args.output_dir)
    model_short = get_model_short_name(args.model)

    # Build sample list
    samples = []
    for fw_name in args.frameworks:
        fw = Framework(fw_name)
        for num in FRAMEWORK_RANGES[fw]:
            samples.append((fw, num))

    if args.limit:
        samples = samples[:args.limit]

    pending = [(fw, num) for fw, num in samples if not is_sample_done(output_dir, fw, num, model_short)]

    print(f"Total: {len(samples)}, Done: {len(samples) - len(pending)}, Pending: {len(pending)}")

    if not pending:
        print("All samples already completed.")
        return

    success = 0
    failed = 0

    for i, (framework, number) in enumerate(pending):
        print(f"[{i+1}/{len(pending)}] {framework.value}/{number}...", end=" ", flush=True)
        start = time.time()

        try:
            code, image_path = load_sample(data_dir, framework, number)
            messages = build_api_messages(framework, code, image_path)
            response = run_api_inference(client, args.model, messages, max_tokens=args.max_tokens)
            parse_and_save(response, output_dir, framework, number, model_short)

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
