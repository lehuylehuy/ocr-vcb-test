# Bắt đầu cho người mới — tự chạy từng lệnh

Tài liệu cầm tay chỉ việc: gõ **từng lệnh một**, Enter, xem kết quả, hiểu chuyện gì đang xảy
ra. Không cần biết trước gì về AI. Làm đúng thứ tự từ trên xuống.

> Quy ước: mỗi ô là **một lệnh** — bôi đen, copy, dán vào Terminal, Enter. Chờ chạy xong mới
> làm lệnh tiếp theo.

---

## 0. Bạn sắp làm gì? (hiểu trong 1 phút)

Đưa vào file **PDF sổ đỏ** → máy tự đọc → trả ra **dữ liệu có cấu trúc** (họ tên, số CCCD,
số thửa, diện tích...) kèm **điểm tin cậy** từng thông tin.

```
   sodo_1.pdf  ──►  [ pipeline ]  ──►  output/sodo_1.json
   (ảnh giấy)                          { "so_cccd": "033184006615", ... }
```

Bên trong có 3 nhân vật: **OCR** đọc chữ + vị trí (mù nghĩa) → **Điều phối** đoán đây là giấy
gì → **VLM** (AI hiểu ảnh) trả lời chữ nào là thông tin gì. Bạn không cần hiểu sâu để chạy.

---

## 1. Chuẩn bị máy (làm 1 lần)

Mở ứng dụng **Terminal** trên Mac. Gõ từng lệnh:

**a) Kiểm tra Python** (Mac thường có sẵn):
```bash
python3 --version
```
Thấy `Python 3.x.x` là được.

**b) Cài Ollama** — phần mềm chạy AI trên máy (miễn phí):
```bash
brew install ollama
```
```bash
brew services start ollama
```
```bash
ollama pull qwen2.5vl:3b
```
Lệnh cuối tải model AI (~3GB), lần đầu hơi lâu. Đây là "bộ não" chạy ngay trên máy bạn.

> Nếu báo `command not found: brew` → cài Homebrew tại https://brew.sh (dán 1 lệnh của họ).

**c) Vào thư mục project** (mọi lệnh sau đều gõ ở đây):
```bash
cd ~/Documents/Project/VCB/vcb-ocr
```

---

## 2. Cài đặt project (làm 1 lần)

**a) Tạo môi trường Python riêng** (gọi là `.venv` — để thư viện project không lẫn với máy):
```bash
python3 -m venv .venv
```

**b) Cài các thư viện project cần** (lần đầu vài phút):
```bash
.venv/bin/pip install -r requirements.txt
```

**c) Tạo file cấu hình `.env`** (chọn dùng Ollama trên Mac):
```bash
cp .env.example .env
```

**d) Chỉnh 1 dòng cho hợp máy Mac** (ảnh nhỏ lại cho vừa "trí nhớ" của Ollama):
```bash
sed -i '' 's/^MAX_SIDE=.*/MAX_SIDE=1024/' .env
```

---

## 3. Chạy pipeline

**a) Nới "trí nhớ" của Ollama** (tránh lỗi `exceeds context size`) — gõ trước mỗi phiên:
```bash
export OLLAMA_CONTEXT_LENGTH=8192
```

**b) Chạy trên file mẫu:**
```bash
.venv/bin/python pipeline.py data/samples/sodo_1.pdf
```

Chạy file khác của bạn — thay đường dẫn:
```bash
.venv/bin/python pipeline.py duong/dan/toi/file.pdf
```

---

## 4. Đọc màn hình kết quả (từng dòng nghĩa gì)

```
  Trang 1: OCR 32 dòng                         ← OCR đọc được 32 cụm chữ trên trang 1
  Trang 1 [sodo_m5_tr1]: 8 field, 8 cần hậu kiểm (18.4s)
           └ nhận ra "sổ đỏ mẫu 5" ─┘   └ AI trích 8 thông tin, 8 cái cần người xem lại
```

Bảng thông tin:
```
  ⚠️ so_cccd     = '033184006615'    conf=0.48
  │   │            │                   └ điểm tin cậy 0–1 (càng cao càng chắc)
  │   │            └ giá trị AI đọc được
  │   └ tên thông tin
  └ dấu ⚠️ = "cần người kiểm tra lại" (điểm tin cậy dưới ngưỡng)
```

**Vì sao mọi dòng đều ⚠️?** Trên Mac (Ollama), điểm tin cậy tính hơi thấp nên máy "thận
trọng", đánh dấu tất cả để người xem. **Đây là hành vi ĐÚNG và an toàn** — thà bắt xem thừa
còn hơn tự duyệt sai. Chạy trên máy GPU thật, điểm tin cậy chính xác hơn, nhiều thông tin sẽ
được tự duyệt.

---

## 5. Đọc file kết quả JSON

Mở `output/sodo_1.json` bằng trình soạn thảo. Mỗi thông tin trông vậy:
```json
"so_cccd": {
  "value": "033184006615",     // giá trị đọc được
  "confidence": 0.48,          // điểm tin cậy
  "bbox": [270, 600, 190, 26], // VỊ TRÍ trên ảnh (x, y, rộng, cao) — để khoanh vùng
  "need_review": true,         // true = cần người xem lại
  "logprob_score": null,       // độ chắc của AI (Ollama không có → null)
  "ocr_agreement": 0.9         // mức khớp với chữ OCR đọc độc lập
}
```
`bbox` để làm gì: màn hình hậu kiểm sau này dùng nó **vẽ khung đỏ** đúng chỗ trên ảnh gốc,
giúp người kiểm tra soi lại nhanh.

---

## 6. Chấm điểm độ chính xác

Muốn biết AI đọc đúng bao nhiêu %, phải cho máy biết **đáp án đúng**. Đáp án để ở
`data/ground_truth/<tên>.json` (đã có sẵn `sodo_1.json` để thử).

```bash
.venv/bin/python evaluate.py output/ data/ground_truth/
```

Đọc kết quả:
```
  Accuracy toàn bộ: 4/7 (57.1%)     ← đọc đúng 4 trên 7 thông tin
```
57% là do trên Mac ảnh bị thu nhỏ cho nhẹ; trên GPU sẽ cao hơn nhiều.

**Dòng CALIBRATION quan trọng nhất:** kiểm tra trong số thông tin máy **tự duyệt** (không
⚠️), bao nhiêu cái đúng. Máy tự duyệt mà sai → nguy hiểm, phải chỉnh. Hiện máy không tự duyệt
cái nào nên an toàn tuyệt đối.

**Muốn chấm file của bạn:** tạo file đáp án `data/ground_truth/<tên_file>.json` (cùng tên với
file trong `output/`), nội dung là giá trị đúng, ví dụ:
```json
{ "so_cccd": "033184006615", "thua_dat_so": "316", "dien_tich_dat_m2": "68,95" }
```

---

## 7. Thử sức mạnh "config-driven" (không cần lập trình)

Điều hay nhất: **bạn dạy AI bằng cách sửa file mô tả, không sửa code.**

Mở `configs/sodo_m5_tr1.json`, tìm dòng `thua_dat_so` (AI đang đọc sai). Sửa `mo_ta` rõ hơn:
```json
"mo_ta": "CHỈ ghi con số sau chữ 'Thửa đất số', KHÔNG chép lại chữ 'Thửa đất số'",
```
Lưu, rồi chạy lại lệnh ở mục 3b. AI đọc theo hướng dẫn mới — **không đụng dòng code nào**. Đây
chính là cách thêm loại giấy mới sau này: chỉ tạo/sửa file cấu hình.

---

## 8. Tóm tắt: lệnh nào làm gì

| Lệnh | Làm gì |
|---|---|
| `python3 -m venv .venv` | tạo môi trường (1 lần) |
| `.venv/bin/pip install -r requirements.txt` | cài thư viện (1 lần) |
| `cp .env.example .env` | tạo cấu hình (1 lần) |
| `export OLLAMA_CONTEXT_LENGTH=8192` | nới trí nhớ Ollama (mỗi phiên Terminal) |
| `.venv/bin/python pipeline.py <pdf>` | **chạy đọc tài liệu** → `output/<tên>.json` |
| `.venv/bin/python evaluate.py output/ data/ground_truth/` | **chấm điểm** so đáp án |

> Mẹo: nếu không muốn gõ `.venv/bin/` mỗi lần, "bật" môi trường một lần bằng
> `source .venv/bin/activate` — sau đó chỉ cần gõ `python pipeline.py ...`. Gõ `deactivate`
> để tắt.

---

## 9. Gặp lỗi? Bảng tra nhanh

| Máy báo | Nghĩa | Làm gì |
|---|---|---|
| `command not found: brew` | chưa có brew | cài tại https://brew.sh |
| lỗi kết nối `11434` / VLM | Ollama chưa chạy | `brew services start ollama` |
| `exceeds context size (4096)` | ảnh quá lớn cho Ollama | `sed -i '' 's/^MAX_SIDE=.*/MAX_SIDE=1024/' .env` |
| `LỖI VLM 404` | sai tên model | so `OCR_MODEL` trong `.env` với `ollama list` |
| mọi field đều ⚠️ | điểm tin cậy thấp (bình thường trên Mac) | không sao — lên GPU sẽ tốt hơn |
| `Không thấy file` | sai đường dẫn PDF | kiểm tra lại đường dẫn |

---

## 10. Tiếp theo

- Chất lượng thật + điểm tin cậy chính xác → chạy trên GPU: [TRIEN_KHAI_VA_TEST.md](TRIEN_KHAI_VA_TEST.md) phần B.
- Hiểu vì sao có OCR + VLM, mô hình dữ liệu → [KIEN_TRUC.md](KIEN_TRUC.md), [MO_HINH_DU_LIEU.md](MO_HINH_DU_LIEU.md).
