---
name: crf-ocr-entry
description: >-
  把纸质/扫描版 CRF（病例报告表）与临床问卷——尤其是含大量手写填答的表格——自动 OCR 识别、抽取为结构化数据集，
  生成 REDCap 标准数据字典 CSV，导出为 Excel/CSV/SAS，并跑 Python 数据质控。当用户要把扫描 CRF/PDF 表单转成
  Excel/SAS/CSV、做 CRF 录入、OCR 识别医学表单、生成数据字典/变量词典、转录手写临床数据、或提到 PaddleOCR /
  PP-Structure / REDCap 数据字典 / EDC 建库时，务必使用本 skill。Use this whenever the user needs to digitize
  scanned case report forms (CRF) or clinical questionnaires — especially handwritten ones — into structured data,
  a REDCap data dictionary, or needs OCR-based medical form data entry and data-quality checking.
---

# CRF 扫描表自动录入（OCR → 数据字典 → 数据库 → 质控）

把纸质 CRF 的扫描件（PDF/图片）变成「干净的结构化数据 + REDCap 数据字典 + 质控报告」。设计上针对**大量手写填答**的场景：PaddleOCR 负责版面/表格/印刷字定位，多模态 LLM 负责读手写内容——两者分工，而不是让单一 OCR 硬啃手写。

## 何时使用

- 用户有一批扫描/拍照的 CRF、问卷、随访表、检查单，想自动录入成数据表；
- 需要生成数据字典/变量词典（REDCap 或中文），或导入 EDC 建库；
- 需要对录入结果做缺失、取值域、一致性、重复值的自动核查；
- 提到 PaddleOCR、PP-Structure、OCR 录入、手写识别、REDCap、数据字典等。

## 总流程（5 步）

```
扫描 CRF（PDF/图片）
  → [1] 版面/表格定位  scripts/ocr_layout.py        （PaddleOCR PP-Structure）
  → [2] 手写字段识别  scripts/extract_handwriting.py （多模态 LLM，读手写/勾选）
  → [3] 生成数据字典  scripts/build_redcap.py        （REDCap CSV + 数据表）
  → [4] 组装数据表    scripts/build_redcap.py        （CSV / Excel / SAS）
  → [5] 数据质控      scripts/quality_check.py       （Python，输出报告）
```

**关键顺序**：先建数据字典（明确"有哪些字段、什么类型、什么取值"），再抽取数据、再做质控。数据字典是质控的输入——没有字典，质控无从判断"什么值非法"。所以不要跳过第 3 步直接抽数据。

## 前置：确认 schema（字段清单）

抽取前必须有一个字段清单 `schema.json`，它是整个流程的"契约"。来源有二：

1. **已有 CRF/方案文档**：先让 Claude 读 CRF 的印刷标签/表头，整理出字段清单（变量名、中文标签、类型、取值域、逻辑校验），写进 `schema.json`。
2. **用户直接提供**：用户给出变量清单或原数据字典。

`schema.json` 格式（字段名直接对应 REDCap 数据字典列）：

```json
{
  "form_name": "baseline",
  "fields": [
    {
      "variable": "age",
      "field_label": "年龄（岁）",
      "field_type": "text",
      "text_validation": "integer",
      "min": "18", "max": "120",
      "choices": "",
      "required": "y",
      "branching_logic": "",
      "value": null
    },
    {
      "variable": "smoking",
      "field_label": "是否吸烟",
      "field_type": "radio",
      "choices": "0, 否 | 1, 是",
      "required": "y",
      "value": null
    }
  ]
}
```

`field_type` 取值遵循 REDCap 规范：`text / notes / radio / dropdown / checkbox / calc / date / yesno / truefalse`。`text_validation` 用 `integer / number / date / phone / email` 等。详见 `references/redcap_dictionary_schema.md`。

## Step 1 — 版面与表格定位（PaddleOCR PP-Structure）

运行：

```bash
python scripts/ocr_layout.py --input crf_scan.pdf --out work/ --lang ch
```

产物：
- `work/layout.json`：每个检测区域的 `{type, text, bbox, page}`（印刷字 + 表格单元格坐标）；
- `work/crops/`：每个区域/单元格的裁剪图（供下一步 LLM 读手写）。

**为什么这步只让 PaddleOCR 做定位、不指望它读手写**：PaddleOCR 对印刷字、中英文混排、表格结构识别很强，但对手写、涂改、勾选框的识别率有限。把它定位到"给出每个单元格的坐标和上下文标签"，手写交给多模态 LLM——分工最稳。

注意：PaddleOCR 各版本 API 差异大，务必先按 `references/paddleocr_setup.md` 固定版本，再调整 `ocr_layout.py` 里结果解析的 key。

## Step 2 — 手写字段识别（多模态 LLM）

运行：

```bash
python scripts/extract_handwriting.py \
  --layout work/layout.json --crops work/crops \
  --schema schema.json --out work/extracted.json \
  --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --model qwen-vl-max --api-key $DASHSCOPE_API_KEY
```

产物 `work/extracted.json`：每条记录一个对象 `{record_id, ...字段: 值}`。

- 脚本走 **OpenAI 兼容接口**，所以 Qwen-VL（DashScope 兼容模式）、GPT-4o、Claude（经代理/兼容层）都能用；`--base-url`/`--model`/`--api-key` 三件套切换。
- 把每个字段的裁剪图连同 `field_label`、`field_type`、`choices` 一起喂给 LLM，让它"读懂标签、按取值域回填"，而不是裸 OCR——这样能显著减少"勾选框填错、单位填错、笔误"。
- 对拿不准的值，脚本会把它标为 `uncertain` 并记录 LLM 理由，留给人工复核（手写数据的可靠性底线）。

## Step 3 & 4 — 生成数据字典 + 组装数据表

运行：

```bash
python scripts/build_redcap.py \
  --schema schema.json \
  --extracted work/extracted.json \
  --out work/ --form-name baseline
```

产物：
- `work/data_dictionary.csv`：REDCap 标准数据字典（含 Variable / Field Name、Form Name、Field Type、Field Label、Choices、Text Validation、Min/Max、Required、Branching Logic 等列），可直接导入 REDCap 建库；
- `work/data.csv`、`work/data.xlsx`：宽表（一行一个受试者，一列一个变量）；
- `work/data.sas7bdat`：若装有 `pyreadstat` 则一并导出 SAS 格式；否则生成 `work/import_data.sas`（PROC IMPORT 读取 CSV 的 SAS 程序）作为替代。

## Step 5 — 数据质控（Python）

运行：

```bash
python scripts/quality_check.py \
  --data work/data.csv \
  --dictionary work/data_dictionary.csv \
  --out work/qc_report.md
```

自动核查并写入报告：
- **完整性**：每个变量的缺失率、缺失模式；
- **取值域**：数值型 min/max 越界、分类变量取值不在 choices 内；
- **一致性**：跨字段逻辑矛盾（如"性别=男"但"妊娠史=有"）、日期先后颠倒；
- **重复**：`record_id` 重复、整行完全重复；
- **类型**：数值列出现非数值、日期格式不合法。

`quality_check.py` 是可扩展模板：一致性规则通常要按项目定制，把它当作起点，往 `rules` 里加项目专属规则。

## 依赖与安装

```bash
# 核心 OCR
pip install paddleocr paddlepaddle
# 手写识别（OpenAI 兼容客户端，Qwen-VL/GPT-4o 等）
pip install openai
# 数据表与导出
pip install pandas openpyxl
# 可选：导出 .sas7bdat
pip install pyreadstat
```

完整、带版本 pin 的安装说明见 `references/paddleocr_setup.md`。

## 常见坑

1. **手写识别靠 LLM，别省这一步**——纯 PaddleOCR 读手写会显著漏读/错读；LLM 视觉是手写场景的底线。
2. **人工复核不可省**——对 `uncertain` 字段、低置信字段必须留一个人机复核清单，尤其是关键结局变量。
3. **隐私**：患者数据请用本地部署（PaddleOCR 本地 + 自建/签约的 LLM 接口），不要用免费在线 OCR 网站。
4. **字段清单先定**：变量名尽量一开始就按 CDISC/REDCap 规范起好（`dm_`/`lb_` 等前缀），后期改字典比改数据表痛苦得多。
5. **PaddleOCR 版本**：不同大版本 API 不兼容，先按 reference 固定版本再跑，别装最新再踩坑。

## 参考文件

- `references/paddleocr_setup.md`：PaddleOCR/PP-Structure 安装、版本 pin、模型与用法。
- `references/redcap_dictionary_schema.md`：REDCap 数据字典各列含义、取值规范、示例。
