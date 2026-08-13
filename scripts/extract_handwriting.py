#!/usr/bin/env python3
"""
Step 2 — 手写字段识别（多模态 LLM）

对每个字段的裁剪图，调用 OpenAI 兼容的多模态接口（Qwen-VL / GPT-4o / Claude 兼容层）
读取手写/勾选值，并按 schema 的 field_label/field_type/choices 约束回填。

产物 <out>/extracted.json：一个 list，每个元素是 {record_id, ...变量: 值}。
对低置信结果，记录到 <out>/uncertain.json 供人工复核。

用法：
  python extract_handwriting.py \
    --layout work/layout.json --crops work/crops --schema schema.json \
    --out work/extracted.json \
    --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
    --model qwen-vl-max --api-key $DASHSCOPE_API_KEY
"""
import argparse
import base64
import json
from pathlib import Path


def encode_image(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def build_prompt(field: dict):
    """按字段约束构造读取指令，让 LLM 读懂标签并按取值域回填。"""
    label = field.get("field_label", field.get("variable", ""))
    ftype = field.get("field_type", "text")
    choices = field.get("choices", "")
    lines = [
        f"请读取这张裁剪图中的手写/勾选内容，它对应表单字段：{label}",
        f"字段类型：{ftype}",
    ]
    if choices:
        lines.append(f"允许取值：{choices}（请只从这些取值中选择）")
    if field.get("text_validation") in ("integer", "number"):
        lines.append("应为数值；若图中留空请返回 null")
    lines.append("只返回一个 JSON：{\"value\": <填写的值或 null>, \"confidence\": \"high/medium/low\", \"reason\": \"一句话说明\"}")
    return "\n".join(lines)


def call_vision(client, model, image_b64, prompt):
    resp = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        }],
        temperature=0,
    )
    return resp.choices[0].message.content


def parse_json_loosely(text: str):
    """LLM 偶尔在 JSON 外包文字，做个宽松提取。"""
    import re
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True)
    ap.add_argument("--crops", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default=None)
    args = ap.parse_args()

    from openai import OpenAI

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    fields = schema["fields"]

    # 简化：单条记录（多记录请按 record 维度扩展本脚本）
    record = {"record_id": schema.get("record_id", "R001")}
    uncertain = []

    crops_dir = Path(args.crops)
    for i, field in enumerate(fields):
        # 找对应裁剪图（此处假设按字段顺序一一对应；实际可按 bbox 匹配）
        crop_path = crops_dir / f"p0_{i}.png"
        if not crop_path.exists():
            continue
        prompt = build_prompt(field)
        raw = call_vision(client, args.model, encode_image(crop_path), prompt)
        parsed = parse_json_loosely(raw)
        value = parsed.get("value")
        conf = parsed.get("confidence", "medium")
        record[field["variable"]] = value
        if conf in ("low", "medium"):
            uncertain.append({"variable": field["variable"], "confidence": conf,
                              "reason": parsed.get("reason"), "raw": raw})

    Path(args.out).write_text(json.dumps([record], ensure_ascii=False, indent=2), encoding="utf-8")
    Path(str(Path(args.out).with_suffix("")) + ".uncertain.json").write_text(
        json.dumps(uncertain, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract_handwriting] 完成：{len(record)-1} 个字段 → {args.out}；低置信 {len(uncertain)} 个见 uncertain 文件")


if __name__ == "__main__":
    main()
