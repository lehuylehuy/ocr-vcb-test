#!/usr/bin/env python3
"""Debug: in ra output THÔ của VLM cho 1 file — prompt gửi đi, response thô, field parse.

Dùng:  .venv/bin/python tools/dump_vlm.py data/samples/oto_1.jpg
       .venv/bin/python tools/dump_vlm.py data/samples/oto_1.jpg --show-prompt
"""
import sys, json, glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL, PDF_DPI, MAX_SIDE
from core.preprocess import load_pages
from core.ocr_client import OcrClient
from core.classify import classify_document
from core.prompt_builder import build_prompt
from core.vlm_client import call_vlm


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_prompt = "--show-prompt" in sys.argv
    if not args:
        sys.exit("Cần đường dẫn file. VD: tools/dump_vlm.py data/samples/oto_1.jpg")
    path = Path(args[0])

    configs = [json.load(open(p)) for p in sorted(glob.glob("configs/*.json"))]
    oc = OcrClient()
    vlm = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    print(f"File: {path}  |  model: {MODEL} @ {BASE_URL}\n")

    pages = list(load_pages(path, dpi=PDF_DPI, max_side=MAX_SIDE))
    pages_words = {pn: oc.infer(img) for pn, img in pages}
    page_config = classify_document(pages_words, configs)

    for pn, img in pages:
        cfg = page_config.get(pn)
        print("=" * 78)
        print(f"TRANG {pn}  →  cấu hình: {cfg['config_id'] if cfg else 'UNKNOWN (bỏ qua)'}")
        print("=" * 78)
        if not cfg:
            print("  (không khớp cấu hình nào — VLM không được gọi)\n")
            continue

        prompt, schema = build_prompt(cfg, pages_words[pn])
        if show_prompt:
            print("\n----- PROMPT GỬI VLM -----")
            print(prompt)
            print("----- HẾT PROMPT -----\n")

        r = call_vlm(vlm, MODEL, img, prompt, schema)
        print("\n----- VLM RESPONSE THÔ -----")
        print((r.get("raw") or "").strip() or "(rỗng)")
        print("\n----- FIELD SAU PARSE -----")
        for k, v in r.get("fields", {}).items():
            flag = "  " if v else "❌"
            print(f"  {flag} {k:24s} = {v!r}")
        if r.get("error"):
            print("  LỖI:", r["error"])
        print()


if __name__ == "__main__":
    main()
