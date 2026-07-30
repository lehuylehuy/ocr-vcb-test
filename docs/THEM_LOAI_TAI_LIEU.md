# Thêm & test nhiều loại tài liệu

Đây là điểm mạnh cốt lõi (config-driven): **mỗi loại giấy = 1 file cấu hình `configs/*.json`.
Pipeline KHÔNG đổi code.** Khi upload, pipeline tự nạp mọi cấu hình và tự nhận đúng loại cho
từng trang qua *trường định danh*.

Repo hiện có 3 loại (đã chạy thật): `sodo_m5_tr1` (sổ đỏ), `dang_ky_oto` (cà vẹt ô tô),
`giay_dkdn` (đăng ký doanh nghiệp).

---

## Công thức thêm 1 loại tài liệu (4 bước)

### Bước 1 — Xem giấy, liệt kê các trường cần lấy
Mở ảnh/PDF mẫu. Ghi ra: cần lấy thông tin gì, mỗi cái kiểu dữ liệu nào (text/number/date/table).

### Bước 2 — Chọn TRƯỜNG ĐỊNH DANH (quan trọng nhất)
Là 1–vài chữ **chỉ xuất hiện ở loại giấy này**, để hệ thống nhận diện. Nguyên tắc:
- Phải **duy nhất** so với các loại khác (sổ đỏ có "Thửa đất số"; cà vẹt có "Số khung").
- Nên chọn chữ OCR **đọc ổn định** (nhãn in rõ). Cà vẹt/CCCD có nhãn song ngữ → chữ tiếng
  Anh ("Chassis", "Engine") thường ổn định hơn vì không dấu.
- `multiple` (cần đủ tất cả) an toàn hơn `single` khi một chữ dễ trùng.

### Bước 3 — Tạo file `configs/<ten>.json`
Copy một file có sẵn rồi sửa. Cấu trúc:
```json
{
  "config_id": "dang_ky_oto",
  "ten": "Giấy đăng ký xe ô tô",
  "type_config": "DKX_OTO",
  "identifier": { "mode": "multiple", "fields": ["Số khung", "Số máy"] },
  "review_mode": "threshold",
  "fields": [
    { "ten": "bien_so", "kieu": "text", "loai": "extract",
      "mo_ta": "biển số đăng ký (No Plate), ví dụ 51H-083.92",
      "use_ocr_hint": true, "min_confidence": 0.97, "regex": null }
  ]
}
```
Giải thích các khoá field:
| Khoá | Nghĩa |
|---|---|
| `ten` | tên trường trong JSON kết quả |
| `kieu` | `text` / `number` / `date` / `table` |
| `loai` | `extract` (AI trích) / `manual` (người nhập) / `compute` (code tính) |
| `mo_ta` | ⭐ mô tả nạp vào prompt AI — viết càng rõ, AI càng đúng |
| `use_ocr_hint` | `true` cho số/mã (giúp AI đỡ đọc nhầm); `false` cho chữ viết tay |
| `min_confidence` | ngưỡng tự-duyệt của trường (xem chính sách 3 bậc dưới) |
| `regex` | luật định dạng; sai luật → luôn bắt hậu kiểm |

**Chính sách `min_confidence` (áp thống nhất cho MỌI loại giấy):** ngưỡng = *mức nghiêm
trọng khi sai × độ dễ sai của loại chữ*. `confidence < min_confidence` → `need_review`.

| Ngưỡng | Dùng cho | Ví dụ |
|---|---|---|
| **0.97** | Số / mã / ngày định danh, số tiền — sai là nghiêm trọng, lại thường ngắn/cấu trúc nên model dễ chắc | CCCD, mã số DN, số khung/máy, biển số, ngày, diện tích, vốn điều lệ, bảng số liệu |
| **0.95** | Tên riêng & giá trị chữ quan trọng — quan trọng nhưng hay sai dấu | tên người/công ty, nhãn hiệu, loại tiền, loại đất |
| **0.90** | Free-text dài, sai vặt, impact thấp — ép cao sẽ bắt hậu kiểm gần như mọi cái | địa chỉ, tên viết tắt |

> Đây là chính sách MẶC ĐỊNH; loại giấy có yêu cầu nghiệp vụ riêng thì chỉnh có chủ đích.
> KHÔNG ép đồng bộ `regex`/`use_ocr_hint`/`columns` giữa các loại — đó là đặc thù từng trường.

### Bước 4 — Chạy
```bash
export OLLAMA_CONTEXT_LENGTH=8192
.venv/bin/python pipeline.py data/samples/oto_1.jpg
```
Pipeline tự nạp **mọi** file trong `configs/` và tự chọn loại đúng. Muốn giới hạn cấu hình:
```bash
.venv/bin/python pipeline.py data/samples/oto_1.jpg --configs configs/dang_ky_oto.json
```

---

## Test nhiều tài liệu cùng lúc

```bash
export OLLAMA_CONTEXT_LENGTH=8192
for f in data/samples/*.pdf data/samples/*.jpg data/samples/*.png; do
  [ -e "$f" ] && .venv/bin/python pipeline.py "$f"
done
```
Mỗi file ra 1 `output/<tên>.json`. Định dạng hỗ trợ: PDF, JPG, PNG, WEBP, TIFF.

### Chấm điểm hàng loạt
Tạo đáp án `data/ground_truth/<tên>.json` cho mỗi file (cùng tên với output), rồi:
```bash
.venv/bin/python evaluate.py output/ data/ground_truth/
```
`evaluate.py` gộp mọi field của mọi loại → accuracy từng field + calibration chung.

---

## Bài học thực tế: phân loại phụ thuộc chất lượng OCR

Khi test cà vẹt ô tô lần đầu, hệ thống báo **`unknown`** dù giấy có "Số khung". Lý do: OCR
mặc định (không phải tiếng Việt) đọc **"Số khung" → "s6 khung"** ("ố"→"6"). Khớp chính xác
trượt.

**Đã xử lý:** nâng `classify.py` sang **khớp mờ (fuzzy)** — chịu được vài ký tự sai
(`FUZZY_THRESHOLD = 0.82`). Sau đó cà vẹt nhận đúng `dang_ky_oto`.

**Giải pháp gốc (khuyến nghị khi lên GPU):** thay recognizer bằng **VietOCR** → đọc đúng dấu,
phân loại chắc chắn hơn, và field chữ tiếng Việt cũng chính xác hơn. Xem
[KIEN_TRUC.md](KIEN_TRUC.md) mục 3.

**Mẹo chọn định danh chống nhiễu OCR:**
- Ưu tiên nhãn tiếng Anh song ngữ (Chassis, Engine, Owner) — không dấu, OCR ít sai.
- Tránh chữ có nhiều dấu làm định danh nếu chưa dùng OCR tiếng Việt.
- Nếu một loại hay bị `unknown`, dump text OCR để xem thực tế đọc ra gì:
  ```bash
  .venv/bin/python -c "from core.preprocess import load_pages; from core.ocr_client import OcrClient; \
  c=OcrClient(); \
  [print(' '.join(w.text for w in c.infer(img))) for _,img in load_pages('data/samples/oto_1.jpg', 250, 2048)]"
  ```

---

## Danh sách loại tài liệu hiện có

| config_id | Loại giấy | Định danh |
|---|---|---|
| `sodo_m5_tr1` | Sổ đỏ mẫu 5 - trang 1 | "Thửa đất số" & "Tờ bản đồ số" |
| `dang_ky_oto` | Giấy đăng ký xe ô tô | "Số khung" & "Số máy" |
| `giay_dkdn` | GCN đăng ký doanh nghiệp | "Mã số doanh nghiệp" & "Vốn điều lệ" |
| `bctc_tt200_cdkt` | BCTC TT200 - Bảng cân đối kế toán (header + bảng, port từ config VCB thật) | "Bảng cân đối kế toán" hoặc "BÁO CÁO TÌNH HÌNH TÀI CHÍNH" |

> **Ghi chú BCTC (nặng bảng):**
> - Field header chạy tốt, ổn định. Field `kieu:table` trả **rows có cấu trúc** theo cột
>   khai trong config (`postprocess.process_table`), mỗi ô có confidence; `max_tokens`
>   đã nâng lên 4096 trong `core/vlm_client.py`.
> - Cần model context lớn: tạo `qwen2.5vl-3b-16k` (Modelfile `PARAMETER num_ctx 16384`)
>   rồi chạy với `OCR_MODEL=qwen2.5vl-3b-16k`.
> - **Giới hạn 3B:** model chỉ trả ~4 dòng đầu rồi tự dừng (`finish_reason=stop`, không
>   phải hết context) — đây là trần năng lực 3B, **7B mới trả đủ dòng**. Cấu trúc/mã số
>   phần trả về thì đúng.
>
> **Đã BỎ — cơ chế "anchor" (bơm danh sách mã OCR vào prompt để ép trả đủ dòng):**
> từng thử để chống 3B dừng sớm, nhưng bơm ~34 mã làm **3B ngợp → 1 dòng rỗng**, nên
> đã gỡ khỏi `core/prompt_builder.py` (2 hàm `_harvest_anchors`/`_anchor_hint` + `import re`).
> **Khi lên 7B, nếu vẫn thiếu dòng, cân nhắc làm lại cơ chế này:** với mỗi cột bảng khai
> `regex`, quét OCR lấy các giá trị đứng độc lập (dùng look-around `(?<![\d.,])…(?![\d.,])`
> để bỏ nhóm 3 chữ số trong số tiền như `698.745.833`), rồi chèn danh sách đó vào prompt
> "trả đủ mỗi giá trị một dòng". 7B đủ sức theo checklist này còn 3B thì không.

Thêm loại mới → thêm 1 dòng vào bảng này cho dễ theo dõi.
