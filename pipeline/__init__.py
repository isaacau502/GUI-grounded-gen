"""End-to-end UI repair pipeline.

Composes:
    screenshot -> grounding model -> structured critique
                                  -> + source code
                                  -> generation LLM (Qwen2.5-VL-72B)
                                  -> repaired code

Evaluation reuses DesignBench's metric pipeline from `ui-repair-baseline/`.
"""
