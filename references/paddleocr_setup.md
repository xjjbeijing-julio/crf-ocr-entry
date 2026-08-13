# PaddleOCR / PP-Structure 安装与使用（版本 pin 建议）

## 为什么先固定版本

PaddleOCR 从 2.x 到 3.x API 变化很大（`PPStructure` 独立类 → `PaddleOCR` 统一入口），
不同版本的返回结构 key 也不同（如 `rec_texts` / `rec_boxes` 的嵌套位置）。
**先固定版本、再跑脚本**，否则 `ocr_layout.py` 里解析结果的 key 对不上。

## 推荐安装（稳定组合）

```bash
# 1) 创建独立环境（强烈建议，避免与其它包冲突）
conda create -n crfocr python=3.10 -y
conda activate crfocr

# 2) PaddlePaddle（GPU 版按 CUDA 版本自选，CPU 版通用）
pip install paddlepaddle   # CPU
# 或 GPU：pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# 3) PaddleOCR（固定到 3.x 一个明确版本，例如）
pip install paddleocr==2.8.1   # 或 3.x 最新稳定版，装完记下版本号

# 4) 依赖
pip install openai pandas openpyxl pillow
pip install pymupdf        # 处理 PDF 输入（ocr_layout.py 需要）
pip install pyreadstat     # 可选：导出 .sas7bdat
```

> 装完后务必跑一句确认版本：
> ```bash
> python -c "import paddleocr; print(paddleocr.__version__)"
> ```

## 首次运行会下载模型

PaddleOCR 首次运行会联网下载识别/检测模型到 `~/.paddlex/` 或 `~/.paddleocr/`。
离线环境需手动下载模型并指定 `model_dir`。

## PP-Structure（表格结构识别）说明

- **版面分析 + 表格结构**是 PaddleOCR 的 PP-Structure 系列能力，3.x 合并进统一 `PaddleOCR` 入口，
  通过参数开启。若你装的版本仍用独立 `PPStructure` 类（2.x），用法不同：

  ```python
  # 2.x 旧 API
  from paddleocr import PPStructure, save_structure_res
  engine = PPStructure(show_log=True)
  result = engine(img_path)
  save_structure_res(result, save_folder, img_name)
  ```

- 表格结构识别的结果里，表格区域会带 `res`（HTML 表格）+ 单元格 `bbox`。对 CRF 这种规整表格，
  **优先用表格识别**拿单元格坐标，再配合多模态 LLM 读单元格里的手写，而不是用普通文本检测。

## 如果 `ocr_layout.py` 结果 key 对不上

在脚本里找到 `res.get("rec_texts")` / `res.get("rec_boxes")` 两行，改成你版本实际返回的 key。
排查方法：

```bash
python -c "
import numpy as np
from paddleocr import PaddleOCR
eng = PaddleOCR(lang='ch', use_doc_orientation_classify=False, use_doc_unwarping=False)
res = eng.predict(input='你的某张图.png')
print(type(res[0]), res[0].keys() if isinstance(res[0], dict) else dir(res[0]))
"
```

把打印出的真实 key 回填到脚本即可。

## 常见问题

- **中文手写**：PaddleOCR 对印刷中文强、手写弱；本 skill 已把手写交给 LLM 视觉，PaddleOCR 只负责定位。
- **GPU 加速**：CPU 也可用，但大批量扫描件建议 GPU，速度差一个量级。
- **内存**：PDF 逐页 200 DPI 渲染会占内存，大批量建议按页流式处理。
