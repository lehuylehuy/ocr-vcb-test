"""Bước 7 — Gộp trang → document. Một tài liệu trải nhiều trang; gộp field lại, ưu tiên
trang có confidence cao hơn. Giữ page_no để hậu kiểm biết vẽ bbox trên ảnh nào."""


def merge_document(page_results: list[dict]) -> dict:
    """page_results: [{page_no, config_id, fields:{ten:{value,confidence,bbox,...}}}]"""
    def _c(info):                     # conf None (server không có logprobs) coi như 0
        c = info.get("confidence")
        return c if isinstance(c, (int, float)) else 0.0

    merged: dict[str, dict] = {}
    for pr in page_results:
        for ten, info in pr["fields"].items():
            keep = info | {"page_no": pr["page_no"]}
            cur = merged.get(ten)
            if cur is None:
                merged[ten] = keep
            elif info.get("kieu") == "table":
                # bảng: giữ trang có nhiều dòng hơn (bảng trải nhiều trang)
                if info.get("n_rows", 0) > cur.get("n_rows", 0):
                    merged[ten] = keep
            elif info.get("value") and (not cur.get("value") or _c(info) > _c(cur)):
                # field thường: lấy non-empty đầu tiên; trùng thì giữ conf cao hơn
                merged[ten] = keep
    confs = [_c(f) for f in merged.values()
             if isinstance(f.get("confidence"), (int, float))
             and (f.get("value") or f.get("kieu") == "table")]
    avg = round(sum(confs) / len(confs), 3) if confs else 0.0
    need = any(f["need_review"] for f in merged.values())
    return {
        "fields": merged,
        "avg_confidence": avg,
        "trang_thai": "cho_xac_nhan" if need else "da_xac_nhan",
    }
