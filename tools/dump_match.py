#!/usr/bin/env python3
"""Debug: cho từng field, in giá trị VLM rồi SO KHỚP với từng dòng OCR (xếp hạng).

Xem tận mắt cách tính ocr_agreement: điểm 'full' (so cả dòng — cách hiện tại) và
'partial' (trượt cửa sổ — cách đề xuất), để hiểu vì sao có field thấp oan.

Dùng:  .venv/bin/python tools/dump_match.py data/samples/oto_1.jpg
       .venv/bin/python tools/dump_match.py data/samples/oto_1.jpg --top 8
"""
import sys, json, glob
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL, PDF_DPI, MAX_SIDE
from core.preprocess import load_pages
from core.ocr_client import OcrClient, strip_accents
from core.classify import classify_document
from core.prompt_builder import build_prompt
from core.vlm_client import call_vlm


def full_ratio(v, line):
    return SequenceMatcher(None, v, line).ratio()


def partial_ratio(v, line):
    if not v or len(v) > len(line):
        return SequenceMatcher(None, v, line).ratio()
    best = 0.0
    for i in range(len(line) - len(v) + 1):
        best = max(best, SequenceMatcher(None, v, line[i:i + len(v)]).ratio())
    return best


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 5
    if not args:
        sys.exit("Cần đường dẫn file. VD: tools/dump_match.py data/samples/oto_1.jpg")
    path = Path(args[0])

    configs = [json.load(open(p)) for p in sorted(glob.glob("configs/*.json"))]
    oc = OcrClient()
    vlm = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    pages = list(load_pages(path, dpi=PDF_DPI, max_side=MAX_SIDE))
    pages_words = {pn: oc.infer(img) for pn, img in pages}
    page_config = classify_document(pages_words, configs)

    for pn, img in pages:
        cfg = page_config.get(pn)
        if not cfg:
            continue
        words = pages_words[pn]
        ocr_lines = [strip_accents(w.text) for w in words]
        prompt, schema = build_prompt(cfg, words)
        r = call_vlm(vlm, MODEL, img, prompt, schema)

        print(f"\n{'#'*80}\nTRANG {pn} [{cfg['config_id']}]\n{'#'*80}")
        for f in cfg["fields"]:
            if f.get("loai") != "extract":
                continue
            value = str(r["fields"].get(f["ten"], "")).strip()
            print(f"\n─── {f['ten']}  |  VLM trả: {value!r}")
            if not value:
                print("      (rỗng — không so khớp)")
                continue
            v = strip_accents(value)
            scored = [(full_ratio(v, ln), partial_ratio(v, ln), ln) for ln in ocr_lines]
            scored.sort(key=lambda x: x[1], reverse=True)
            print(f"      {'full':>5} {'partial':>8}   dòng OCR")
            for full, part, ln in scored[:top]:
                mark = "←KHỚP NHẤT" if part == scored[0][1] else ""
                print(f"      {full:>5.2f} {part:>8.2f}   {ln[:52]!r} {mark}")
            best_full = max(s[0] for s in scored)
            best_part = max(s[1] for s in scored)
            print(f"      → ocr_agreement HIỆN TẠI (full) = {best_full:.2f}"
                  f"   |   nếu partial = {best_part:.2f}")


if __name__ == "__main__":
    main()
