#!/usr/bin/env python3
"""Pipeline VCB OCR — điều phối toàn bộ luồng trích xuất cho 1 tài liệu.

  Preprocess → OCR nhỏ → Phân loại trang → Dựng prompt → VLM → Post-process → Gộp trang

Chạy:
  python pipeline.py data/samples/sodo_1.pdf --configs configs/sodo_m5_tr1.json
  python pipeline.py data/samples/sodo_1.pdf                 # tự nạp mọi config trong configs/

Kết quả: output/<tên>.json
"""
import argparse, json, sys, time
from pathlib import Path

from openai import OpenAI

from config import API_KEY, BASE_URL, MAX_SIDE, MODEL, PDF_DPI
from core.preprocess import load_pages
from core.ocr_client import OcrClient
from core.classify import classify_document
from core.prompt_builder import build_prompt
from core.vlm_client import call_vlm
from core.postprocess import process_page
from core.merge import merge_document


def load_configs(paths: list[Path]) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in paths]


def process(doc_path: Path, configs: list[dict], out_dir: Path) -> dict:
    client = OcrClient()
    vlm = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    print(f"VLM: {MODEL} @ {BASE_URL}\nTài liệu: {doc_path}\n")

    # 1+2. Render + OCR mọi trang
    pages, pages_words = [], {}
    for page_no, img in load_pages(doc_path, dpi=PDF_DPI, max_side=MAX_SIDE):
        words = client.infer(img)
        pages.append((page_no, img))
        pages_words[page_no] = words
        print(f"  Trang {page_no}: OCR {len(words)} dòng")

    # 3. Phân loại trang → cấu hình
    page_config = classify_document(pages_words, configs)

    # 4-6. Với mỗi trang đã khớp: dựng prompt → VLM → post-process
    page_results = []
    for page_no, img in pages:
        cfg = page_config.get(page_no)
        if cfg is None:
            print(f"  Trang {page_no}: unknown (không khớp cấu hình) — bỏ qua")
            continue
        words = pages_words[page_no]
        prompt, schema = build_prompt(cfg, words)
        t0 = time.time()
        r = call_vlm(vlm, MODEL, img, prompt, schema)
        dt = time.time() - t0
        if r["error"]:
            print(f"  Trang {page_no} [{cfg['config_id']}]: LỖI VLM — {r['error']} ({dt:.1f}s)")
            continue
        fields = process_page(r["fields"], cfg, r["logprobs"], words)
        page_results.append({"page_no": page_no, "config_id": cfg["config_id"], "fields": fields})
        nrev = sum(1 for f in fields.values() if f["need_review"])
        print(f"  Trang {page_no} [{cfg['config_id']}]: {len(fields)} field, "
              f"{nrev} cần hậu kiểm ({dt:.1f}s)")

    # 7. Gộp trang → document
    doc = merge_document(page_results) if page_results else {"fields": {}, "avg_confidence": 0, "trang_thai": "loi"}
    result = {"source": str(doc_path), "model": MODEL,
              "document": {k: doc[k] for k in ("avg_confidence", "trang_thai")},
              "fields": doc["fields"], "pages": page_results}

    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{doc_path.stem}.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nKết quả: {out_file}  (trạng thái: {doc['trang_thai']}, "
          f"conf TB: {doc['avg_confidence']})")
    for ten, f in doc["fields"].items():
        flag = "⚠️ " if f["need_review"] else "  "
        if f.get("kieu") == "table":
            print(f"  {flag}{ten:22s} = [bảng {f.get('n_rows', 0)} dòng] conf={f['confidence']}")
        else:
            print(f"  {flag}{ten:22s} = {f['value']!r:40s} conf={f['confidence']}")
    return result


def main():
    ap = argparse.ArgumentParser(description="Pipeline VCB OCR")
    ap.add_argument("doc", type=Path, help="đường dẫn PDF/ảnh")
    ap.add_argument("--configs", nargs="*", type=Path, help="các file cấu hình; mặc định: configs/*.json")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.exit(f"Không thấy file: {args.doc}")
    cfg_paths = args.configs or sorted((Path(__file__).parent / "configs").glob("*.json"))
    if not cfg_paths:
        sys.exit("Không có cấu hình nào trong configs/")
    process(args.doc, load_configs(cfg_paths), args.out)


if __name__ == "__main__":
    main()
