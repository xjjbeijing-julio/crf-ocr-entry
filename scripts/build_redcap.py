#!/usr/bin/env python3
"""
Step 3 & 4 — 生成 REDCap 数据字典 + 组装数据表

输入 schema.json（字段清单）+ extracted.json（抽取结果），输出：
  - data_dictionary.csv   REDCap 标准数据字典（可直接导入 REDCap 建库）
  - data.csv / data.xlsx  宽表（一行一个受试者，一列一个变量）
  - data.sas7bdat         若装 pyreadstat；否则 import_data.sas（PROC IMPORT 程序）

用法：
  python build_redcap.py --schema schema.json --extracted work/extracted.json \
    --out work/ --form-name baseline
"""
import argparse
import csv
import json
from pathlib import Path

import pandas as pd

# REDCap 数据字典标准列（顺序与 REDCap 导入模板一致）
REDCAP_COLUMNS = [
    "Variable / Field Name",
    "Form Name",
    "Section Header",
    "Field Type",
    "Field Label",
    "Choices, Calculations, OR Slider Labels",
    "Field Note",
    "Text Validation Type OR Show Slider Number",
    "Text Validation Min",
    "Text Validation Max",
    "Identifier?",
    "Branching Logic (Show field only if...)",
    "Required Field?",
    "Custom Alignment",
    "Question Number (surveys only)",
    "Matrix Group Name",
    "Matrix Ranking?",
    "Field Annotation",
]


def field_to_row(field: dict, form_name: str) -> dict:
    return {
        "Variable / Field Name": field.get("variable", ""),
        "Form Name": form_name,
        "Section Header": field.get("section_header", ""),
        "Field Type": field.get("field_type", "text"),
        "Field Label": field.get("field_label", ""),
        "Choices, Calculations, OR Slider Labels": field.get("choices", ""),
        "Field Note": field.get("field_note", ""),
        "Text Validation Type OR Show Slider Number": field.get("text_validation", ""),
        "Text Validation Min": field.get("min", ""),
        "Text Validation Max": field.get("max", ""),
        "Identifier?": field.get("identifier", ""),
        "Branching Logic (Show field only if...)": field.get("branching_logic", ""),
        "Required Field?": field.get("required", ""),
        "Custom Alignment": field.get("custom_alignment", ""),
        "Question Number (surveys only)": "",
        "Matrix Group Name": "",
        "Matrix Ranking?": "",
        "Field Annotation": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--form-name", default="baseline")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    fields = schema["fields"]

    # 1) 数据字典
    with (out / "data_dictionary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REDCAP_COLUMNS)
        writer.writeheader()
        for field in fields:
            writer.writerow(field_to_row(field, args.form_name))

    # 2) 数据表（宽表）
    records = json.loads(Path(args.extracted).read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    # 列顺序对齐 schema
    cols = [c for c in ["record_id"] + [f["variable"] for f in fields] if c in df.columns]
    df = df[cols]
    df.to_csv(out / "data.csv", index=False, encoding="utf-8-sig")
    df.to_excel(out / "data.xlsx", index=False)

    # 3) SAS
    try:
        import pyreadstat
        df.to_csv(out / "_tmp_for_sas.csv", index=False, encoding="utf-8")
        pyreadstat.write_sas7bdat(df, str(out / "data.sas7bdat"))
        (out / "_tmp_for_sas.csv").unlink(missing_ok=True)
        print("[build_redcap] 已导出 data.sas7bdat")
    except ImportError:
        sas = "PROC IMPORT DATAFILE='data.csv' OUT=work.data DBMS=CSV REPLACE;\n  GUESSINGROWS=200;\nRUN;\n"
        (out / "import_data.sas").write_text(sas, encoding="utf-8")
        print("[build_redcap] 未装 pyreadstat，已生成 import_data.sas（用 PROC IMPORT 读 CSV）")

    print(f"[build_redcap] 完成：数据字典 data_dictionary.csv、数据表 data.csv / data.xlsx")


if __name__ == "__main__":
    main()
