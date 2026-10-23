"""Render a plain-Chinese single-reviewer calibration form from blind cases."""

from __future__ import annotations

import json
from pathlib import Path

WORKSHEET = Path("evals/reviews/scoring-human-comparison-v1/worksheet.jsonl")
OUTPUT = Path("docs/evaluations/single-reviewer-coarse-calibration-form.md")


def render_form(rows: list[dict[str, object]]) -> str:
    lines = [
        "# 12 题轻量人工校准表",
        "",
        "你不需要懂代码或四维评分。每题只看回答质量，选一个：`差`、`一般` 或 `好`，",
        "再选是否应该交给人工复核（`是`／`否`），最后用一句自然语言说明原因即可。",
        "",
        "这是一位评审的粗粒度校准，不是双盲人工一致性研究。请不要查看",
        "`author_key.json`，也不要根据你猜测的系统预期来打分。",
        "",
        "## 判断参考",
        "",
        "- **差**：核心结论错误、几乎没有回答问题，或有明显危险误导。",
        "- **一般**：方向大体正确，但漏了关键条件、步骤或风险。",
        "- **好**：结论正确，解释了原因/边界/取舍，表达也清楚。",
        "- **需要复核 = 是**：你觉得回答模糊、存在事实风险，或无法仅凭题目判断。",
        "",
        "请把每题末尾两行复制到聊天里即可，例如：`blind-01：好；否；说明了证据不足时的边界。`",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['blind_id']}",
                "",
                f"**问题**：{row['question']}",
                "",
                f"**回答**：{row['answer']}",
                "",
                "- 质量（差／一般／好）：`_____`",
                "- 需要复核（是／否）：`_____`",
                "- 一句原因：`_____`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    rows = [json.loads(line) for line in WORKSHEET.read_text(encoding="utf-8").splitlines() if line]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_form(rows), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "row_count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
