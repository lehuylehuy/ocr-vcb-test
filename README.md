# VCB OCR — Pipeline trích xuất tài liệu bằng OCR + VLM

Số hóa hồ sơ giấy ngân hàng (CCCD, sổ đỏ, BCTC, giấy ĐKKD...) thành **dữ liệu có cấu trúc,
đủ tin cậy** để hệ thống nghiệp vụ dùng trực tiếp. Kiến trúc lai: **OCR nhỏ** đọc chữ +
toạ độ, **VLM** hiểu ngữ nghĩa và trích field theo **cấu hình do người dùng khai báo**.

## Ba đặc trưng cốt lõi

1. **Config-driven** — khai *tài liệu có trường nào, mô tả ra sao* bằng file cấu hình.
   Thêm loại giấy mới = thêm cấu hình, **không sửa code, không train model**.
2. **Human-in-the-loop** — mỗi field có **confidence**; cổng tự duyệt theo ngưỡng (mặc định
   97%), chỉ trường dưới ngưỡng mới cần người hậu kiểm.
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
| [docs/BAT_DAU_CHO_NGUOI_MOI.md](docs/BAT_DAU_CHO_NGUOI_MOI.md) | 👶 **Người mới bắt đầu ở đây** — chạy từ số 0, giải thích từng dòng |
| [docs/THEM_LOAI_TAI_LIEU.md](docs/THEM_LOAI_TAI_LIEU.md) | ➕ **Thêm & test nhiều loại tài liệu** — chỉ thêm file JSON, không sửa code |
| [docs/TODO_CAI_TIEN_LIEN_TUC.md](docs/TODO_CAI_TIEN_LIEN_TUC.md) | 🔄 TODO nghiên cứu sau — "bánh đà dữ liệu" (train lại, human-in-the-loop) |
| [docs/KIEN_TRUC.md](docs/KIEN_TRUC.md) | Kiến trúc, 3 vai (OCR đọc · điều phối quyết · VLM hiểu), I/O từng bước, bảo mật |
| [docs/MO_HINH_DU_LIEU.md](docs/MO_HINH_DU_LIEU.md) | Loại tài liệu · Cấu hình · Trường · Hệ thống — ERD + SQL |
| [docs/TRIEN_KHAI_VA_TEST.md](docs/TRIEN_KHAI_VA_TEST.md) | **Hướng dẫn cài đặt, chạy, test (Mac dev + GPU thuê)** |
| [GPU_TEST_PLAN.md](GPU_TEST_PLAN.md) | Checklist test trên GPU thuê (RunPod) |

## Chạy nhanh (đã kiểm chứng trên Mac)

Người mới hoàn toàn: làm theo [docs/BAT_DAU_CHO_NGUOI_MOI.md](docs/BAT_DAU_CHO_NGUOI_MOI.md)
(giải thích từng lệnh). Tóm tắt các lệnh:
```bash
cd ~/Documents/Project/VCB/vcb-ocr
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                                   # trỏ Ollama qwen2.5vl:3b
sed -i '' 's/^MAX_SIDE=.*/MAX_SIDE=1024/' .env         # Mac: ảnh nhỏ cho vừa context
export OLLAMA_CONTEXT_LENGTH=8192                       # nới context Ollama
.venv/bin/python pipeline.py data/samples/sodo_1.pdf   # chạy
.venv/bin/python evaluate.py output/ data/ground_truth/# chấm điểm
```

> Trên Mac (Ollama) đặt `MAX_SIDE=1024` trong `.env` do context nhỏ. Trên GPU (vLLM) dùng
> `MAX_SIDE=2048` — xem [docs/TRIEN_KHAI_VA_TEST.md](docs/TRIEN_KHAI_VA_TEST.md).

## Cấu trúc

```
vcb-ocr/
├── config.py               # đọc .env (chọn model)
├── configs/                # ⭐ cấu hình tài liệu (mô phỏng DB) — prompt sinh từ đây
│   └── sodo_m5_tr1.json
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
