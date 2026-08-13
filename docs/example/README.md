# 运行示例（虚构数据）

这是整个流水线 Step 3 → 4 → 5 的**可复现示例**。Step 1（版面定位）和 Step 2（手写识别）需要真实扫描件 + 多模态 LLM 接口，故此处用一份**模拟的「手写抽取结果」**（`extracted.json`）直接喂给后续步骤，让你在无需 OCR/LLM 的情况下看到脚本的真实输入输出。

> ⚠️ **所有数据均为虚构**，仅用于演示脚本用法与质控报告格式，不涉及任何真实患者信息。

## 文件清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `schema.json` | 手写 | 字段清单（契约）：6 个字段的类型 / 取值域 / 校验 |
| `extracted.json` | 手写（模拟 Step 2 输出） | 5 条记录，**故意埋了 5 类错误** |
| `data_dictionary.csv` | Step 3 生成 | REDCap 标准数据字典，可直接导入建库 |
| `data.csv` | Step 4 生成 | 宽表（一行一个受试者，一列一个变量） |
| `qc_report.md` | Step 5 生成 | 数据质控报告 |

## 故意埋的错误（用于演示质控报告）

| 记录 | 问题 | 质控报告对应章节 |
|---|---|---|
| R002 | 年龄 `150` 越界（合法 18–120） | 二、取值域 |
| R002 | 既往病史缺失 | 一、完整性 |
| R003 | 年龄 `abc` 非数值 | 二、取值域 |
| R003 | 吸烟取值 `2` 非法（合法 0/1） | 二、取值域 |
| R003 | 日期 `2026/08/12` 格式错（应为 `YYYY-MM-DD`） | 五、格式核查 |
| R003（重复） | `record_id` 重复出现两次 | 四、重复核查 |
| R003 | 收缩压 `300` 越界（合法 60–250） | 二、取值域 |
| R005 | 年龄缺失 | 一、完整性 |

## 复现命令

在**仓库根目录**运行：

```bash
# Step 3 & 4：数据字典 + 数据表
python scripts/build_redcap.py \
  --schema docs/example/schema.json \
  --extracted docs/example/extracted.json \
  --out docs/example --form-name baseline

# Step 5：质控报告
python scripts/quality_check.py \
  --data docs/example/data.csv \
  --dictionary docs/example/data_dictionary.csv \
  --out docs/example/qc_report.md
```

运行后，`qc_report.md` 会把上面 8 处错误逐一抓出来，并给出缺失率、非法取值、越界、重复、格式问题。
