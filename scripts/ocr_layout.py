#!/usr/bin/env python3
"""
Step 1 — 版面与表格定位（PaddleOCR / PP-Structure）

对扫描 CRF 做版面分析与文字检测，输出：
  - <out>/layout.json   每个区域的 {type, text, bbox, page}（bbox 为 [x0,y0,x1,y1] 归一化像素坐标）
  - <out>/crops/        每个区域裁剪图（供 Step 2 的多模态 LLM 读手写）

用法：
  python ocr_layout.py --input crf_scan.pdf --out work/ --lang ch

说明：
  PaddleOCR 不同大版本 API 差异较大，本脚本针对 3.x 统一 API 编写，
  并做了 key 兼容。若与你安装的版本不符，先看 references/paddleocr_setup.md 固定版本。
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def _to_axis_bbox(box):
    """把任意 bbox（四点或 [x0,y0,x1,y1]）规整成轴对齐 [x0,y0,x1,y1]。"""
    pts = np.asarray(box, dtype=float).reshape(-1, 2)
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    return [float(x0), float(y0), float(x1), float(y1)]


def crop_region(img: Image.Image, bbox):
    x0, y0, x1, y1 = bbox
    w, h = img.size
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    if x1 <= x0 or y1 <= y0:
        return None
    return img.crop((x0, y0, x1, y1))


def load_images(path: Path):
    """加载 PDF 或单张/多张图片，返回 list[PIL.Image]。"""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise SystemExit("处理 PDF 需要 PyMuPDF：pip install pymupdf")
        doc = fitz.open(str(path))
        imgs = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            imgs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        return imgs
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return [Image.open(path).convert("RGB")]
    raise SystemExit(f"不支持的输入格式：{suffix}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="扫描 CRF 的 PDF 或图片路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--lang", default="ch", help="OCR 语言：ch/en/...")
    args = ap.parse_args()

    out = Path(args.out)
    crop_dir = out / "crops"
    out.mkdir(parents=True, exist_ok=True)
    crop_dir.mkdir(parents=True, exist_ok=True)

    from paddleocr import PaddleOCR

    engine = PaddleOCR(
        lang=args.lang,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    imgs = load_images(Path(args.input))
    regions = []
    for page_idx, img in enumerate(imgs):
        result = engine.predict(input=np.asarray(img))
        for res in result:
            # 兼容不同版本返回结构：统一到 dict
            if isinstance(res, dict):
                d = res.get("res", res)
            else:
                d = {"rec_texts": getattr(res, "rec_texts", None),
                     "rec_boxes": getattr(res, "rec_boxes", None)}
            texts = d.get("rec_texts") or []
            boxes = d.get("rec_boxes") or []
            for i, (t, b) in enumerate(zip(texts, boxes)):
                axis = _to_axis_bbox(b)
                region = {"type": "text", "text": str(t), "bbox": axis, "page": page_idx}
                regions.append(region)
                crop = crop_region(img, axis)
                if crop is not None:
                    crop.save(crop_dir / f"p{page_idx}_{i}.png")

    (out / "layout.json").write_text(
        json.dumps(regions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ocr_layout] 完成：{len(regions)} 个区域 → {out/'layout.json'}, 裁剪图 → {crop_dir}")


if __name__ == "__main__":
    main()
