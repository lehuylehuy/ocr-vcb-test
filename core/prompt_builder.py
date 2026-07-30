"""Bước 4 — Dựng prompt (config-driven): sinh prompt + JSON schema TỪ cấu hình.

Đây là trái tim của "config-driven": prompt KHÔNG viết tay, mà sinh ra từ cấu hình do
người dùng khai báo. Thêm loại giấy mới = thêm file config, không sửa code.

Chỉ đưa field `loai == "extract"` vào prompt (bỏ manual/compute).
Chỉ chèn mỏ neo OCR cho field `use_ocr_hint == true`.
"""
from .ocr_client import Word


def _extract_fields(config: dict) -> list[dict]:
    return [f for f in config["fields"] if f.get("loai") == "extract"]


def _table_item_schema(field: dict) -> dict:
    """1 dòng bảng = object có đúng các cột đã khai trong config (giả lập DB).

    Cột có "regex" → ép guided decoding đúng định dạng (vd Mã chỉ tiêu chỉ cho chữ
    số, chặn model nhét 'A'/'B'/'I' của mục lớn vào cột mã).
    """
    cols = field.get("columns", [])
    if not cols:                               # bảng chưa khai cột → object tự do
        return {"type": "object"}
    props = {}
    for c in cols:
        p = {"type": "string"}
        rgx = c.get("regex")
        if rgx:
            core = rgx.lstrip("^").rstrip("$")
            p["pattern"] = f"^({core})?$"          # rỗng HOẶC khớp
        props[c["ten"]] = p
    return {"type": "object", "properties": props,
            "required": [c["ten"] for c in cols], "additionalProperties": False}


def build_json_schema(config: dict) -> dict:
    """Schema cho guided decoding của vLLM — ép model trả đúng JSON, không lệch."""
    props, required = {}, []
    for f in _extract_fields(config):
        if f.get("kieu") == "table":
            # field bảng: MẢNG các dòng, mỗi dòng là object theo cột đã khai
            props[f["ten"]] = {"type": "array", "items": _table_item_schema(f)}
            required.append(f["ten"])
            continue
        prop = {"type": "string"}
        rgx = f.get("regex")
        if rgx:
            core = rgx.lstrip("^").rstrip("$")       # bỏ neo của user rồi tự bọc lại
            prop["pattern"] = f"^({core})?$"          # rỗng HOẶC khớp; hợp lệ cả xgrammar lẫn Ollama
        props[f["ten"]] = prop
        required.append(f["ten"])
    return {"type": "object", "properties": props,
            "required": required, "additionalProperties": False}


def build_prompt(config: dict, ocr_words: list[Word] | None = None) -> tuple[str, dict]:
    """Trả về (prompt_text, json_schema)."""
    fields = _extract_fields(config)
    parts = []

    # KHỐI 1 — vai trò + bối cảnh
    parts.append(f'Bạn là hệ thống trích xuất thông tin từ giấy tờ. Ảnh đính kèm là một '
                 f'trang "{config["ten"]}". Chỉ trích xuất, không diễn giải.')

    # KHỐI 2 — mỏ neo OCR (chỉ field bật use_ocr_hint), phòng đọc nhầm chuỗi số/mã
    hinted = [f for f in fields if f.get("use_ocr_hint")]
    if hinted and ocr_words:
        lines = "\n".join(f"  ({w.bbox[0]},{w.bbox[1]}) {w.text}" for w in ocr_words)
        parts.append("Chữ OCR đọc được từ ảnh (CÓ THỂ SAI, kèm toạ độ x,y để định vị):\n"
                     f"{lines}\n"
                     "Lưu ý layout: nhãn có thể SONG NGỮ (Việt/Anh); GIÁ TRỊ của một trường "
                     "có thể nằm CÙNG DÒNG hoặc DÒNG NGAY DƯỚI nhãn; giấy có thể chia 2 CỘT "
                     "trái/phải. Hãy dùng danh sách OCR trên để không bỏ sót trường nào.\n"
                     "Ưu tiên ẢNH. Nếu ảnh khác OCR, TIN ẢNH.")

    # KHỐI 3 — schema + mô tả (mô tả nạp thẳng vào đây)
    lines = []
    for f in fields:
        desc = f' ({f["mo_ta"]})' if f.get("mo_ta") else ""
        if f["kieu"] == "table":
            cols = f.get("columns", [])
            col_desc = "; ".join(
                f'"{c["ten"]}"' + (f' = {c["mo_ta"]}' if c.get("mo_ta") else "")
                for c in cols)
            keys = ", ".join(f'"{c["ten"]}"' for c in cols)
            lines.append(
                f'  - {f["ten"]}{desc} — là MẢNG các dòng; MỖI DÒNG là một object '
                f'có đúng các khoá [{keys}]. Ý nghĩa từng cột: {col_desc}.\n'
                f'    Liệt kê ĐẦY ĐỦ TỪNG dòng của bảng = mỗi dòng một object. '
                f'KHÔNG gộp nhóm, KHÔNG tóm tắt, KHÔNG bỏ dòng; ô trống để "".')
        else:
            lines.append(f'  - {f["ten"]}{desc}')
    parts.append("Trích xuất các trường sau (mô tả trong ngoặc giúp xác định đúng vị "
                 "trí):\n" + "\n".join(lines))

    # KHỐI 4 — luật hành xử chống bịa
    parts.append('Quy tắc:\n'
                 '- Trường không có trên trang này → để chuỗi rỗng "".\n'
                 '- KHÔNG suy đoán, KHÔNG bịa. Chỉ ghi thứ đọc rõ trên ảnh.\n'
                 '- Giữ nguyên tiếng Việt có dấu.')

    # KHỐI 5 — ràng buộc đầu ra
    empty = "{" + ", ".join(
        (f'"{f["ten"]}":[]' if f["kieu"] == "table" else f'"{f["ten"]}":""')
        for f in fields) + "}"
    parts.append(f"Trả về DUY NHẤT một JSON, không thêm chữ nào khác:\n{empty}")

    return "\n\n".join(parts), build_json_schema(config)
