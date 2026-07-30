#!/usr/bin/env python3
"""So sánh Tesseract vs PaddleOCR (RapidOCR/PP-OCR) trên tài liệu tiếng Việt.

Đo 2 thứ:
  1. FULL-PAGE TEXT: đọc được bao nhiêu, dấu tiếng Việt có đúng không (nhìn mắt).
  2. KEY FIELDS: các giá trị đã biết trên sổ đỏ có xuất hiện chính xác trong text không.

Chạy: .venv/bin/python eval/compare_ocr.py data/samples/sodo_1.pdf
"""
import sys, time, re, unicodedata
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image

DPI = 250

# Giá trị đã biết trên trang 1 sổ đỏ (ground truth để chấm recall field)
KEY_VALUES = {
    "ho_ten":        "Nguyễn Thị Hương",
    "so_cccd":       "033184006615",
    "thua_dat_so":   "316",
    "to_ban_do_so":  "87",
    "dien_tich":     "68,95",
    "loai_dat":      "ODT",
    "dia_danh":      "Hải Dương",
}


def pdf_page1(pdf_path: Path) -> Image.Image:
    pdf = pdfium.PdfDocument(str(pdf_path))
    img = pdf[0].render(scale=DPI / 72).to_pil().convert("RGB")
    return img


def norm(s: str) -> str:
    """Chuẩn hoá để so khớp: gộp khoảng trắng, giữ dấu tiếng Việt."""
    return re.sub(r"\s+", " ", s).strip()


def score_fields(text: str) -> dict:
    """Với mỗi field, kiểm tra chuỗi có xuất hiện nguyên vẹn trong text OCR không."""
    t = norm(text)
    t_nospace = t.replace(" ", "")
    res = {}
    for k, v in KEY_VALUES.items():
        v1 = norm(v)
        hit = (v1 in t) or (v1.replace(" ", "") in t_nospace)
        res[k] = hit
    return res


# ---------------- Engine 1: Tesseract ----------------
def run_tesseract(img: Image.Image):
    import pytesseract
    t0 = time.time()
    text = pytesseract.image_to_string(img, lang="vie")
    dt = time.time() - t0
    return text, dt, None  # tesseract image_to_string không trả bbox ở đây


# ---------------- Engine 2: RapidOCR (PP-OCR / PaddleOCR ONNX) ----------------
_rapid = None
def run_rapidocr(img: Image.Image):
    global _rapid
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    if _rapid is None:
        _rapid = RapidOCR()
    t0 = time.time()
    result, _ = _rapid(np.array(img))
    dt = time.time() - t0
    # result: [[box, text, conf], ...]
    lines = [r[1] for r in result] if result else []
    confs = [float(r[2]) for r in result] if result else []
    text = "\n".join(lines)
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    return text, dt, {"n_lines": len(lines), "avg_conf": avg_conf}


def report(name, text, dt, extra):
    fields = score_fields(text)
    n_hit = sum(fields.values())
    print(f"\n{'='*70}\n{name}\n{'='*70}")
    print(f"  Thời gian: {dt:.1f}s", end="")
    if extra:
        print(f" | {extra}", end="")
    print()
    print(f"  Field đọc đúng: {n_hit}/{len(fields)}")
    for k, v in KEY_VALUES.items():
        mark = "✓" if fields[k] else "✗"
        print(f"    {mark} {k:14s} (mong đợi: {v})")
    print(f"\n  --- TEXT THÔ (200 ký tự đầu) ---")
    print("  " + norm(text)[:200].replace("\n", " "))
    return n_hit, len(fields)


def main():
    pdf = Path(sys.argv[1] if len(sys.argv) > 1 else "data/samples/sodo_1.pdf")
    print(f"Tài liệu: {pdf}  | DPI={DPI}")
    img = pdf_page1(pdf)
    out = Path("eval_out"); out.mkdir(exist_ok=True)
    img.save(out / "page1.png")
    print(f"Ảnh render: {out/'page1.png'}  ({img.width}x{img.height})")

    results = {}
    for name, fn in [("TESSERACT (lang=vie)", run_tesseract),
                     ("RAPIDOCR / PP-OCR (≈PaddleOCR)", run_rapidocr)]:
        try:
            text, dt, extra = fn(img)
            (out / f"{name.split()[0].lower()}.txt").write_text(text, encoding="utf-8")
            results[name] = report(name, text, dt, extra)
        except Exception as e:
            print(f"\n{name}: LỖI — {e}")
            results[name] = (0, len(KEY_VALUES))

    print(f"\n\n{'#'*70}\nKẾT LUẬN\n{'#'*70}")
    for name, (hit, total) in results.items():
        print(f"  {name:38s}: {hit}/{total} field")
    print(f"\n  Text đầy đủ đã lưu ở eval_out/*.txt để xem dấu tiếng Việt.")


if __name__ == "__main__":
    main()
