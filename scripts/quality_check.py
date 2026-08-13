#!/usr/bin/env python3
"""
Step 5 — 数据质控（Python）

读数据表 + REDCap 数据字典，自动核查并生成 Markdown 质控报告：
  - 完整性：各变量缺失率
  - 取值域：数值 min/max 越界、分类取值不在 choices 内
  - 一致性：可扩展的跨字段规则（下方 rules 列表按项目定制）
  - 重复：record_id 重复、整行重复
  - 类型：数值列含非数值、日期格式不合法

用法：
  python quality_check.py --data work/data.csv --dictionary work/data_dictionary.csv --out work/qc_report.md
"""
import argparse
import csv
import re
from pathlib import Path

import pandas as pd


def parse_choices(s: str):
    """REDCap choices 形如 '0, 否 | 1, 是'，提取合法取值集合。"""
    if not s:
        return None
    vals = set()
    for part in s.split("|"):
        code = part.strip().split(",")[0].strip()
        if code:
            vals.add(code)
    return vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--dictionary", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.data, dtype=str)
    meta = {}
    with open(args.dictionary, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            meta[row["Variable / Field Name"]] = row

    report = ["# 数据质控报告", "", f"记录数：{len(df)}；变量数：{len(df.columns)}", ""]

    # 1) 缺失率
    report.append("## 一、完整性（缺失率）")
    missing = df.isna().sum() / len(df)
    for var, rate in missing.items():
        if rate > 0:
            report.append(f"- `{var}`：缺失 {rate:.1%}")
    if (missing == 0).all():
        report.append("- 无缺失。")

    # 2) 取值域
    report.append("\n## 二、取值域核查")
    for var in df.columns:
        m = meta.get(var)
        if not m:
            continue
        choices = parse_choices(m.get("Choices, Calculations, OR Slider Labels", ""))
        if choices:
            illegal = set(df[var].dropna().unique()) - choices
            if illegal:
                report.append(f"- `{var}` 出现非合法取值：{sorted(illegal)}")
        # 数值越界
        vtype = m.get("Text Validation Type OR Show Slider Number", "")
        if vtype in ("integer", "number"):
            numeric = pd.to_numeric(df[var], errors="coerce")
            bad_type = df[var][numeric.isna() & df[var].notna()]
            if len(bad_type):
                report.append(f"- `{var}` 含非数值：{bad_type.tolist()[:10]}")
            lo = m.get("Text Validation Min", "")
            hi = m.get("Text Validation Max", "")
            if lo or hi:
                out_of_range = numeric[(numeric < float(lo or "-inf")) | (numeric > float(hi or "inf"))]
                if len(out_of_range):
                    report.append(f"- `{var}` 越界（{lo}~{hi}）：{out_of_range.tolist()[:10]}")

    # 3) 一致性（项目定制规则，示例）
    report.append("\n## 三、一致性核查")
    rules = [
        # ("性别=男 但 妊娠=有", lambda d: (d.get("gender") == "1") & (d.get("pregnant") == "1")),
    ]
    for name, fn in rules:
        flag = fn(df)
        if flag.any():
            report.append(f"- 违反规则「{name}」：{int(flag.sum())} 条")

    # 4) 重复
    report.append("\n## 四、重复核查")
    if "record_id" in df.columns:
        dup_id = df["record_id"].duplicated().sum()
        report.append(f"- `record_id` 重复：{dup_id} 条")
    dup_rows = df.duplicated().sum()
    report.append(f"- 整行完全重复：{dup_rows} 条")

    # 5) 类型/格式
    report.append("\n## 五、格式核查")
    for var in df.columns:
        m = meta.get(var)
        if m and m.get("Text Validation Type OR Show Slider Number", "") == "date":
            bad = df[var][df[var].notna() & ~df[var].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")]
            if len(bad):
                report.append(f"- `{var}` 日期格式不合法（应为 YYYY-MM-DD）：{bad.tolist()[:10]}")

    Path(args.out).write_text("\n".join(report), encoding="utf-8")
    print(f"[quality_check] 完成：{args.out}")


if __name__ == "__main__":
    main()
