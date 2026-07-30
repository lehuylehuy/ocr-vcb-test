"""Bước 6a — Tính CONFIDENCE cho từng field (nền tảng của cổng tự-duyệt 97%).

confidence LẤY TỪ VLM (logprob của chính model), KHÔNG trộn OCR:
  conf = logprob_score   — độ chắc của model, từ logprobs (nếu server trả về).

OCR chỉ còn dùng để TÌM BBOX (định vị vùng field trên ảnh), không tham gia tính conf.
regex vẫn là luật cứng: sai định dạng thì ép người xem dù model chắc mấy.
Server không trả logprobs → không đo được conf (None) → ép hậu kiểm.
"""
from __future__ import annotations
import math, re
from difflib import SequenceMatcher
from .ocr_client import Word


def logprob_for_value(value: str, logprobs: list[dict] | None) -> float | None:
    """Ước lượng độ chắc của model cho `value`: khớp value vào chuỗi token, lấy trung bình
    logprob các token phủ lên value. Không có logprobs → None."""
    if not logprobs or not value:
        return None
    toks, offsets, pos = [], [], 0
    full = ""
    for lp in logprobs:
        t = lp["token"]
        offsets.append((pos, pos + len(t), lp["logprob"]))
        full += t
        pos += len(t)
    idx = full.find(value)
    if idx == -1:
        # value bị token hoá rời (dấu, số) → fallback: trung bình toàn bộ token
        vals = [lp["logprob"] for lp in logprobs]
        return math.exp(sum(vals) / len(vals)) if vals else None
    a, b = idx, idx + len(value)
    picked = [lg for (s, e, lg) in offsets if e > a and s < b]
    return math.exp(sum(picked) / len(picked)) if picked else None


def best_ocr_match(value: str, words: list[Word]) -> tuple[float, Word | None]:
    """Tìm Word OCR giống `value` nhất → (điểm giống 0..1, Word)."""
    best_r, best_w = 0.0, None
    for w in words:
        r = SequenceMatcher(None, value, w.text).ratio()
        if r > best_r:
            best_r, best_w = r, w
    return best_r, best_w


def score_field(value: str, field_cfg: dict, logprobs, ocr_words) -> dict:
    """Trả về {confidence, need_review, bbox, logprob_score, ocr_agreement}.

    confidence = logprob của VLM (chỉ tín hiệu model). OCR chỉ để lấy bbox.
    """
    lp = logprob_for_value(value, logprobs)
    # OCR chỉ để định vị bbox — KHÔNG tham gia tính confidence
    agreement, matched = best_ocr_match(value, ocr_words) if value else (0.0, None)

    if not value:                           # rỗng: model bảo không có → để người xem
        conf = 0.0
    elif lp is not None:
        conf = lp                           # lấy thẳng từ VLM
    else:                                   # server không trả logprobs → không đo được
        conf = None

    # Luật cứng: sai regex → chặn tự duyệt (guard định dạng, không phải OCR)
    rgx = field_cfg.get("regex")
    if value and rgx and conf is not None and not re.match(rgx, value):
        conf = min(conf, 0.50)

    min_conf = field_cfg.get("min_confidence", 0.97)
    need_review = (conf is None) or (conf < min_conf)
    return {
        "confidence": round(conf, 3) if conf is not None else None,
        "need_review": need_review,
        "bbox": list(matched.bbox) if (matched and agreement >= 0.6) else None,
        "logprob_score": round(lp, 3) if lp is not None else None,
        "ocr_agreement": round(agreement, 3),   # chỉ để tham khảo, không vào conf
    }
