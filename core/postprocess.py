"""Bước 6b — Post-process: ép kiểu dữ liệu + gắn confidence/bbox cho từng field.

Chuẩn hoá bằng CODE những gì đáng tin hơn là dặn model (số, đơn vị). Sau đó chấm điểm.
"""
from __future__ import annotations
import re
from .confidence import score_field, logprob_for_value


def coerce(value: str, kieu: str) -> str:
    """Ép kiểu nhẹ, giữ dạng chuỗi để hiển thị. Không phá dữ liệu gốc."""
    v = (value or "").strip()
    if kieu == "number":
        v = re.sub(r"\s*m[²2]\s*$", "", v)          # '68,95m²' -> '68,95'
        v = v.strip()
    return v


# ───────────────────────── Field dạng bảng ─────────────────────────

def _table_rows(raw) -> list:
    """Bóc list các dòng thô từ output model (chịu vài dạng model hay trả)."""
    if isinstance(raw, dict):
        return raw.get("rows") or []
    if isinstance(raw, list):
        return raw
    return []                         # str (bị cắt cụt) / None → không có dòng


def _row_cells(row, col_names: list[str]) -> dict:
    """1 dòng thô → dict cell keyed theo ĐÚNG cột đã khai trong config."""
    if isinstance(row, dict):
        return {c: str(row.get(c, "") or "").strip() for c in col_names}
    if isinstance(row, list):         # fallback: model trả mảng theo thứ tự cột
        return {c: (str(row[i]).strip() if i < len(row) else "")
                for i, c in enumerate(col_names)}
    return {c: "" for c in col_names}


def process_table(raw, field_cfg: dict, logprobs) -> dict:
    """Bảng → field có cấu trúc theo CỘT ĐÃ KHAI trong config (giả lập DB).

    Mỗi dòng: {cells: {<cột>: giá trị}, confidence, need_review}.
    confidence từng dòng = trung bình logprob VLM của các ô có nội dung (bỏ rỗng/'-').
    """
    col_names = [c["ten"] for c in field_cfg.get("columns", [])]
    min_conf = field_cfg.get("min_confidence", 0.97)
    rows_out, row_confs = [], []
    for row in _table_rows(raw):
        cells = _row_cells(row, col_names)
        vals = [logprob_for_value(v, logprobs) for v in cells.values()
                if v and v.strip() not in ("-", "")]
        vals = [v for v in vals if v is not None]
        rconf = round(sum(vals) / len(vals), 3) if vals else None
        row_confs.append(rconf if rconf is not None else 0.0)
        rows_out.append({
            "cells": cells,
            "confidence": rconf,
            "need_review": (rconf is None) or (rconf < min_conf),
        })
    avg = round(sum(row_confs) / len(row_confs), 3) if row_confs else None
    return {
        "kieu": "table",
        "columns": col_names,
        "n_rows": len(rows_out),
        "rows": rows_out,
        "confidence": avg,
        "need_review": any(r["need_review"] for r in rows_out) if rows_out else True,
    }


def process_page(vlm_fields: dict, config: dict, logprobs, ocr_words) -> dict:
    """Gắn confidence + bbox cho mọi field extract của 1 trang."""
    out = {}
    for f in config["fields"]:
        if f.get("loai") != "extract":
            continue
        if f.get("kieu") == "table":
            out[f["ten"]] = process_table(vlm_fields.get(f["ten"]), f, logprobs)
            continue
        raw = str(vlm_fields.get(f["ten"], "") or "")
        value = coerce(raw, f["kieu"])
        s = score_field(value, f, logprobs, ocr_words)
        out[f["ten"]] = {"value": value, "kieu": f["kieu"], **s}
    return out
