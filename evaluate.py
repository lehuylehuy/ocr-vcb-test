#!/usr/bin/env python3
"""Đánh giá pipeline: so kết quả output/ với nhãn tay data/ground_truth/.

Đo 3 thứ:
  1. Accuracy từng field (exact + normalized: bỏ dấu cách, chuẩn hoá số/ngày).
  2. Accuracy tổng thể.
  3. CALIBRATION — trong các field pipeline TỰ DUYỆT (need_review=false), bao nhiêu % đúng?
     Đây là câu hỏi sống còn: nếu tự duyệt mà sai nhiều → ngưỡng/công thức confidence hỏng.

Chạy: python evaluate.py output/ data/ground_truth/
"""
import json, sys, re
from pathlib import Path


def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace(".", "").replace(",", "")     # 68,95 ~ 6895 ; 1.250 ~ 1250
    return s


def match(pred: str, gold: str) -> bool:
    return norm(pred) == norm(gold) or (bool(norm(gold)) and norm(gold) in norm(pred))


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "output")
    gt_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "data/ground_truth")

    per_field = {}      # ten -> [đúng, tổng]
    auto = [0, 0]       # [đúng, tổng] trong nhóm tự duyệt
    review = [0, 0]     # [đúng, tổng] trong nhóm cần hậu kiểm
    total = [0, 0]

    gts = sorted(gt_dir.glob("*.json"))
    if not gts:
        sys.exit(f"Không có nhãn trong {gt_dir}. Tạo file <tên>.json khớp với output/.")

    for gt_file in gts:
        pred_file = out_dir / gt_file.name
        if not pred_file.exists():
            print(f"⚠️  thiếu output cho {gt_file.name}, bỏ qua")
            continue
        gold = json.loads(gt_file.read_text(encoding="utf-8"))
        pred = json.loads(pred_file.read_text(encoding="utf-8"))["fields"]

        for ten, gval in gold.items():
            if not str(gval).strip():
                continue
            pinfo = pred.get(ten, {})
            pval = pinfo.get("value", "")
            ok = match(pval, gval)
            per_field.setdefault(ten, [0, 0])
            per_field[ten][1] += 1; per_field[ten][0] += ok
            total[1] += 1; total[0] += ok
            bucket = review if pinfo.get("need_review") else auto
            bucket[1] += 1; bucket[0] += ok

    print(f"\n{'='*60}\nACCURACY TỪNG FIELD\n{'='*60}")
    for ten, (c, n) in sorted(per_field.items()):
        print(f"  {ten:24s} {c}/{n}  ({100*c/n:.0f}%)")

    print(f"\n{'='*60}\nTỔNG THỂ\n{'='*60}")
    print(f"  Accuracy toàn bộ: {total[0]}/{total[1]} ({100*total[0]/max(total[1],1):.1f}%)")

    print(f"\n{'='*60}\nCALIBRATION (chất lượng cổng tự-duyệt)\n{'='*60}")
    if auto[1]:
        print(f"  TỰ DUYỆT (need_review=false): {auto[0]}/{auto[1]} đúng "
              f"({100*auto[0]/auto[1]:.1f}%)  ← muốn ≥ ngưỡng (vd 97%)")
    if review[1]:
        print(f"  CẦN HẬU KIỂM (need_review=true): {review[0]}/{review[1]} đúng "
              f"({100*review[0]/review[1]:.1f}%)  ← thấp là ĐÚNG (đáng ngờ nên bắt xem)")
    if auto[1]:
        wrong_auto = auto[1] - auto[0]
        print(f"\n  → {wrong_auto} field bị tự duyệt NHƯNG SAI. "
              f"{'TỐT' if wrong_auto == 0 else 'NGUY HIỂM — nâng ngưỡng/chỉnh confidence'}")


if __name__ == "__main__":
    main()
