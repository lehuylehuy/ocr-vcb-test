"""Bước 2 — OCR nhỏ (vai "đọc chữ"): ảnh → text + toạ độ + độ tin cậy.

Hợp đồng dữ liệu `Word` cố định. Engine: PaddleOCR lang='vi' — đọc dấu tiếng Việt + mã/số
tốt, sạch (xem so sánh 3 engine: eval/KET_QUA_DANH_GIA.md). Sau này lên Triton chỉ thay
thân hàm `infer`, phần còn lại của pipeline không đổi một dòng.
"""
from __future__ import annotations
import unicodedata
from dataclasses import dataclass
import numpy as np


@dataclass
class Word:
    text: str
    bbox: tuple            # (x, y, w, h) — góc trên-trái + rộng + cao, theo pixel ảnh
    conf: float


def strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt để khớp bất chấp lỗi dấu. 'Thửa'→'Thua', 'đ'→'d'."""
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower()


def _poly_to_bbox(poly) -> tuple:
    """4 điểm (hoặc nhiều) → (x, y, w, h) hộp bao."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x, y = min(xs), min(ys)
    return int(x), int(y), int(max(xs) - x), int(max(ys) - y)


class OcrClient:
    """Vỏ bọc PaddleOCR (lang='vi'). Đổi engine = đổi class này, hợp đồng Word giữ nguyên."""

    def __init__(self):
        self._engine = None

    def _lazy(self):
        if self._engine is None:
            from paddleocr import PaddleOCR
            self._engine = PaddleOCR(lang="vi", use_textline_orientation=True)
        return self._engine

    def infer(self, img) -> list[Word]:
        """Đọc 1 ảnh → danh sách Word. bbox chuẩn hoá về (x, y, w, h)."""
        engine = self._lazy()
        words: list[Word] = []
        for r in engine.predict(np.array(img)):
            texts = r.get("rec_texts", [])
            scores = r.get("rec_scores", [])
            polys = r.get("rec_polys") or r.get("dt_polys") or []
            for text, score, poly in zip(texts, scores, polys):
                words.append(Word(text=str(text).strip(),
                                  bbox=_poly_to_bbox(poly), conf=float(score)))
        return words
