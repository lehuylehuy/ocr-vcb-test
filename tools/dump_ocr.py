#!/usr/bin/env python3
"""Debug: in ra output THÔ của OcrClient cho 1 file (mọi trang).

Dùng:  .venv/bin/python tools/dump_ocr.py data/samples/oto_1.jpg
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PDF_DPI, MAX_SIDE
from core.preprocess import load_pages
from core.ocr_client import OcrClient, strip_accents


def main():
    if len(sys.argv) < 2:
        sys.exit("Cần đường dẫn file. VD: tools/dump_ocr.py data/samples/oto_1.jpg")
    path = Path(sys.argv[1])
    oc = OcrClient()
    print(f"File: {path}  | OCR=PaddleOCR(vi) | DPI={PDF_DPI} MAX_SIDE={MAX_SIDE}\n")

    for page_no, img in load_pages(path, dpi=PDF_DPI, max_side=MAX_SIDE):
        words = oc.infer(img)
        print(f"{'='*78}\nTRANG {page_no}  |  ảnh {img.width}x{img.height}  |  {len(words)} dòng OCR\n{'='*78}")
        print(f"{'#':>3}  {'bbox [x,y,w,h]':<24} {'conf':>5}  text")
        print("-" * 78)
        for i, w in enumerate(words):
            bbox = f"[{w.bbox[0]},{w.bbox[1]},{w.bbox[2]},{w.bbox[3]}]"
            print(f"{i:>3}  {bbox:<24} {w.conf:>5.2f}  {w.text}")
        avg = sum(w.conf for w in words) / len(words) if words else 0
        print(f"\n  → {len(words)} dòng, conf trung bình {avg:.3f}")
        print(f"  → text ghép (bỏ dấu, để soi khớp định danh):")
        print("    " + strip_accents(" ".join(w.text for w in words))[:400])
        print()


if __name__ == "__main__":
    main()
