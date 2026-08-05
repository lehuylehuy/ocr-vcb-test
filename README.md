# VCB OCR — Pipeline trích xuất tài liệu bằng OCR + VLM

Số hóa hồ sơ giấy ngân hàng (CCCD, sổ đỏ, BCTC, giấy ĐKKD...) thành **dữ liệu có cấu trúc,
đủ tin cậy** để hệ thống nghiệp vụ dùng trực tiếp. Kiến trúc lai: **OCR nhỏ** đọc chữ +
toạ độ, **VLM** hiểu ngữ nghĩa và trích field theo **cấu hình do người dùng khai báo**.

## Ba đặc trưng cốt lõi

1. **Config-driven** — khai *tài liệu có trường nào, mô tả ra sao* bằng file cấu hình.
   Thêm loại giấy mới = thêm cấu hình, **không sửa code, không train model**.
2. **Human-in-the-loop** — mỗi field có **confidence**; cổng tự duyệt theo ngưỡng khai
   trong config (chính sách 3 bậc 0.90/0.95/0.97 — xem [docs/THEM_LOAI_TAI_LIEU.md](docs/THEM_LOAI_TAI_LIEU.md)),
   chỉ trường dưới ngưỡng mới cần người hậu kiểm.
3. **Giải thích được** — mỗi giá trị gắn **bounding box** trỏ về vị trí gốc trên ảnh.

## Luồng pipeline

```
Preprocess → OCR nhỏ → Phân loại trang → Dựng prompt → VLM → Post-process → Gộp trang
  (ảnh)      (text+bbox)  (khớp định danh)  (từ config)  (JSON) (conf+bbox)   (document)
```

Chi tiết: [docs/KIEN_TRUC.md](docs/KIEN_TRUC.md).

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [docs/THEM_LOAI_TAI_LIEU.md](docs/THEM_LOAI_TAI_LIEU.md) | ➕ **Thêm & test loại tài liệu** — chỉ thêm file JSON; chính sách ngưỡng `min_confidence` |
| [docs/KIEN_TRUC.md](docs/KIEN_TRUC.md) | Kiến trúc, 3 vai (OCR đọc · điều phối quyết · VLM hiểu), I/O từng bước, bảo mật |
| [docs/MO_HINH_DU_LIEU.md](docs/MO_HINH_DU_LIEU.md) | Loại tài liệu · Cấu hình · Trường · Hệ thống — ERD + SQL |
| [docs/TRIEN_KHAI_VA_TEST.md](docs/TRIEN_KHAI_VA_TEST.md) | **Hướng dẫn cài đặt, chạy, test (Mac dev + GPU UAT)** |

## Cài đặt

```bash
cd ~/Documents/Project/VCB/vcb-ocr
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Chọn "bộ não" — sửa `.env` (bật/tắt 1 khối, không sửa code)

`.env` có sẵn 2 khối, đổi môi trường = comment khối này / bỏ comment khối kia:

| Môi trường | Model | Yêu cầu bật trước |
|---|---|---|
| **UAT / GPU 32GB** (mặc định) | vLLM + `Qwen3-VL-8B-Instruct` | `vllm serve Qwen/Qwen3-VL-8B-Instruct --max-model-len 16384 --port 8000` (cần vLLM đủ mới hỗ trợ Qwen3-VL) |
| **Mac dev** | Ollama + `qwen2.5vl-3b-16k` | `ollama pull qwen2.5vl:3b` + tạo bản context 16k (xem TRIEN_KHAI_VA_TEST) |

## Chạy

```bash
# BCTC (có field bảng theo cột)
.venv/bin/python pipeline.py data/samples/bctc_tt200_cdkt_p1.pdf --configs configs/bctc_tt200_cdkt.json
# Sổ đỏ (tự nạp mọi config trong configs/ rồi chọn loại đúng)
.venv/bin/python pipeline.py data/samples/sodo_1.pdf
# Chấm điểm so ground_truth
.venv/bin/python evaluate.py output/ data/ground_truth/
```

Kết quả ở `output/<tên>.json`. Chi tiết cài đặt/serve từng môi trường:
[docs/TRIEN_KHAI_VA_TEST.md](docs/TRIEN_KHAI_VA_TEST.md).

## Cấu trúc

```
vcb-ocr/
├── config.py               # đọc .env (chọn model)
├── configs/                # ⭐ cấu hình tài liệu (mô phỏng DB) — prompt sinh từ đây
│   ├── sodo_m5_tr1.json     #   sổ đỏ · dang_ky_oto · giay_dkdn
│   └── bctc_tt200_cdkt.json #   BCTC (port từ config VCB thật, có field bảng)
├── core/
│   ├── preprocess.py       # PDF → ảnh
│   ├── ocr_client.py       # OCR nhỏ → Word{text,bbox,conf} (đổi sang Triton sau)
│   ├── classify.py         # khớp trường định danh → chọn cấu hình cho trang
│   ├── prompt_builder.py   # ⭐ build_prompt + build_json_schema TỪ cấu hình
│   ├── vlm_client.py       # gọi VLM (OpenAI API) + logprobs
│   ├── confidence.py       # logprob + đối chiếu OCR + regex → confidence
│   ├── postprocess.py      # ép kiểu, gán bbox, chấm điểm
│   └── merge.py            # gộp trang → document
├── pipeline.py             # điều phối toàn bộ
├── evaluate.py             # so ground_truth → accuracy + calibration
├── data/samples/           # PDF mẫu
├── data/ground_truth/      # nhãn tay để đánh giá
└── docs/                   # tài liệu
```

## Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Pipeline lõi (OCR + VLM + confidence + bbox) | ✅ Chạy được (Mac Ollama + GPU vLLM) |
| Đánh giá + calibration | ✅ Chạy được |
| Tầng dịch vụ (Sanic API + Redis + MinIO) | ⏳ Chưa |
| Tầng cấu hình (DB + UI khai báo) | ⏳ Chưa (nay dùng file JSON) |
