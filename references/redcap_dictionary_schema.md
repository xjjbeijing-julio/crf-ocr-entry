# REDCap 数据字典（Data Dictionary）规范

本 skill 生成的 `data_dictionary.csv` 采用 REDCap 官方数据字典格式，可直接通过
REDCap → Project Setup → Data Dictionary 上传建库。

## 必需列（最少 4 列）

| 列名 | 说明 |
|---|---|
| `Variable / Field Name` | 变量名：小写字母/数字/下划线，不能以数字开头，不能含空格 |
| `Form Name` | 所属表单名（同一表单下所有字段填同一值） |
| `Field Type` | 字段类型（见下） |
| `Field Label` | 显示标签，可含中文 |

## 常用可选列

| 列名 | 说明 |
|---|---|
| `Section Header` | 分组标题行（在字段间插入一个 `text` 型伪字段，label 即标题） |
| `Choices, Calculations, OR Slider Labels` | 单选/复选/下拉的取值：`代码, 标签 \| 代码, 标签` |
| `Field Note` | 字段说明/填表提示 |
| `Text Validation Type OR Show Slider Number` | 文本校验：`integer / number / date / phone / email / zipcode` 等 |
| `Text Validation Min` / `Max` | 数值/日期范围 |
| `Identifier?` | `y` 表示标识字段（如住院号/身份证，导出时受限） |
| `Branching Logic (Show field only if...)` | 显示逻辑，如 `[smoking] = '1'` |
| `Required Field?` | `y` = 必填 |

## Field Type 取值

| 值 | 含义 | 备注 |
|---|---|---|
| `text` | 单行文本/数值 | 配合 Text Validation 校验 |
| `notes` | 多行文本 | |
| `radio` | 单选（圆钮） | 需填 Choices |
| `dropdown` | 下拉单选 | 需填 Choices |
| `checkbox` | 多选 | 需填 Choices，值为多个代码 |
| `yesno` / `truefalse` | 是/否 | 无需 Choices |
| `calc` | 计算字段 | 填 Calculation |
| `date` | 日期 | 配合 `date_ymd` 等校验 |

## Choices 格式

```
0, 否 | 1, 是 | 9, 不详
```

- 用 `|` 分隔各选项，每个选项是 `代码, 标签`。
- 代码用数字或短字符串；标签可中文。

## 变量命名建议（CDISC 风格前缀）

- `dm_` 人口学（demographics）
- `lb_` 实验室（lab）
- `vs_` 生命体征（vital signs）
- `ae_` 不良事件
- `cm_` 合并用药
- `mh_` 病史

从一开始按规范起名，后期跨表合并、SAS 程序、统计建模都会省事。

## 最小示例

```csv
Variable / Field Name,Form Name,Field Type,Field Label,Choices, Calculations, OR Slider Labels,Text Validation Type OR Show Slider Number,Required Field?
record_id,baseline,text,受试者编号,,,y
age,baseline,text,年龄（岁）,,integer,y
smoking,baseline,radio,是否吸烟,"0, 否 | 1, 是",,y
```

（第一列不要有 BOM 之外的隐藏字符；中文标签可直接写。）
