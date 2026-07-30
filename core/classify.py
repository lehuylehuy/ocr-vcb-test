"""Bước 3 — Phân loại trang (vai "điều phối quyết"): dùng text OCR để nhận ra trang là
cấu hình nào, bằng cách khớp TRƯỜNG ĐỊNH DANH. Code thuần, không AI → giải thích được.

- Single:   chỉ cần 1 chuỗi định danh xuất hiện.
- Multiple: phải xuất hiện ĐỦ tất cả các chuỗi.

Khớp BỎ DẤU + KHỚP MỜ (fuzzy) để chịu nhiễu OCR: recognizer mặc định không phải tiếng Việt
nên hay đọc sai ('Số khung' -> 's6 khung', 'ơ'->'o'...). Khớp chính xác sẽ trượt; fuzzy chịu
được vài ký tự sai. Giải pháp gốc là dùng recognizer tiếng Việt (VietOCR).
"""
from difflib import SequenceMatcher
from .ocr_client import Word, strip_accents

FUZZY_THRESHOLD = 0.82   # tỷ lệ giống tối thiểu để coi là "có xuất hiện"


def _page_text_no_accent(words: list[Word]) -> str:
    return strip_accents(" ".join(w.text for w in words))


def fuzzy_contains(text: str, key: str, threshold: float = FUZZY_THRESHOLD) -> bool:
    """key có xuất hiện gần đúng trong text không? Trượt cửa sổ độ dài len(key)."""
    if key in text:                       # khớp chính xác trước cho nhanh
        return True
    L = len(key)
    if L < 4 or len(text) < L:
        return False
    best = 0.0
    for i in range(len(text) - L + 1):
        r = SequenceMatcher(None, key, text[i:i + L]).ratio()
        if r > best:
            best = r
            if best >= threshold:
                return True
    return False


def classify_page(words: list[Word], candidate_configs: list[dict]) -> dict | None:
    """Trả về cấu hình khớp cho trang, hoặc None nếu không trang nào khớp (unknown)."""
    page = _page_text_no_accent(words)
    for cfg in candidate_configs:
        idf = cfg["identifier"]
        keys = [strip_accents(k) for k in idf["fields"]]
        if idf["mode"] == "single":
            if any(fuzzy_contains(page, k) for k in keys):
                return cfg
        else:  # multiple — cần đủ tất cả
            if all(fuzzy_contains(page, k) for k in keys):
                return cfg
    return None


def classify_document(pages_words: dict[int, list[Word]],
                      candidate_configs: list[dict]) -> dict[int, dict | None]:
    """Phân loại mọi trang của 1 tài liệu.

    Tối ưu: nếu folder chỉ có 1 cấu hình thì gán thẳng, bỏ qua khớp định danh
    (nhưng vẫn cần OCR cho bbox + đối chiếu — đã chạy ở bước trước)."""
    if len(candidate_configs) == 1:
        return {p: candidate_configs[0] for p in pages_words}
    return {p: classify_page(w, candidate_configs) for p, w in pages_words.items()}
