# Hướng dẫn triển khai & test

Hai môi trường: **A. Dev trên Mac** (Ollama, không GPU — để hoàn thiện logic) và
**B. Test trên GPU thuê** (vLLM — để đo chất lượng thật). Code giống hệt, chỉ đổi `.env`.

---

## A. Dev trên Mac (đã kiểm chứng chạy được)

### A.1 Cài đặt

```bash
cd ~/Documents/Project/VCB/vcb-ocr
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Ollama (bộ não dev) — nếu chưa có
brew install ollama
brew services start ollama
ollama pull qwen2.5vl:3b

# Tesseract tiếng Việt (tùy chọn, cho đánh giá OCR)
brew install tesseract tesseract-lang
```

### A.2 Cấu hình

```bash
cp .env.example .env
```
Trên Mac, sửa `.env` → **`MAX_SIDE=1024`** (context Ollama nhỏ). Đồng thời tăng context:
```bash
export OLLAMA_CONTEXT_LENGTH=8192      # đặt trước khi chạy, hoặc thêm vào ~/.zshrc
brew services restart ollama
```
> Vì sao: ảnh 2048px sinh nhiều visual token, vượt context mặc định 4096 của Ollama →
> lỗi `exceeds context size`. Trên GPU (vLLM) không gặp vì đặt `max-model-len 16384`.

### A.3 Chạy pipeline

```bash
.venv/bin/python pipeline.py data/samples/sodo_1.pdf
# hoặc chỉ định cấu hình cụ thể:
.venv/bin/python pipeline.py data/samples/sodo_1.pdf --configs configs/sodo_m5_tr1.json
```
Kết quả: `output/sodo_1.json` — mỗi field có `value`, `confidence`, `bbox`, `need_review`.

### A.4 Đánh giá

```bash
# tạo nhãn tay cho mỗi PDF: data/ground_truth/<tên>.json  (khớp tên với output/)
.venv/bin/python evaluate.py output/ data/ground_truth/
```
Đọc 3 chỉ số: **accuracy từng field**, **tổng thể**, và **calibration** (trong nhóm tự-duyệt
bao nhiêu % đúng — quan trọng nhất).

> Lưu ý: Ollama thường **không trả logprobs** → confidence chỉ dựa đối chiếu OCR, sẽ thấp và
> mọi field bị gắn hậu kiểm. Đây là kỳ vọng ở dev — confidence thật cần GPU (bước B).

---

## B. Test trên GPU thuê (RunPod)

Mục tiêu: chạy với **ảnh full 2048px + logprobs thật + model 7B** để đo chất lượng thật và
hiệu chuẩn ngưỡng confidence. Chi phí ~1–2 USD/buổi. Checklist ở [../GPU_TEST_PLAN.md](../GPU_TEST_PLAN.md).

### B.1 Chuẩn bị TRƯỚC khi thuê (làm trên Mac, không tốn tiền GPU)
1. Pipeline chạy ổn ở bước A.
2. **Gán nhãn ≥10–20 tài liệu** vào `data/ground_truth/` — không có thì không đo được gì.
3. Đẩy code lên git (hoặc chuẩn bị rsync).

### B.2 Tạo pod
1. runpod.io → Deploy → Pods → GPU **RTX 4090 24GB** (hoặc L40S 48GB), disk 40–60GB.
2. Template **RunPod PyTorch 2.x**. Expose port **8000** nếu muốn gọi từ Mac.
3. Running → mở Web Terminal.

### B.3 Cài & chạy vLLM (trên pod)
```bash
pip install -U vllm openai rapidocr-onnxruntime pypdfium2 pillow python-dotenv
git clone <repo> /workspace/vcb-ocr && cd /workspace/vcb-ocr

vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
  --port 8000 --served-model-name ocr-extractor \
  --max-model-len 16384 --limit-mm-per-prompt image=2 \
  --gpu-memory-utilization 0.92 > /workspace/vllm.log 2>&1 &
tail -f /workspace/vllm.log        # chờ "Uvicorn running on ... :8000"
curl http://localhost:8000/v1/models
```
Nếu OOM: giảm `--max-model-len 8192`, hoặc dùng `Qwen/Qwen2.5-VL-7B-Instruct-AWQ`, hoặc GPU 48GB.
Nếu báo không hỗ trợ model: `pip install -U vllm transformers`, kiểm tra tên tag trên HuggingFace.

### B.4 Chạy pipeline (trên pod)
`.env` trên pod:
```
OCR_BASE_URL=http://localhost:8000/v1
OCR_MODEL=ocr-extractor
OCR_API_KEY=dummy
PDF_DPI=250
MAX_SIDE=2048
```
```bash
python pipeline.py data/samples/sodo_1.pdf
# chạy hàng loạt:
for f in data/samples/*.pdf; do python pipeline.py "$f"; done
python evaluate.py output/ data/ground_truth/
```

### B.5 Đọc kết quả & hiệu chuẩn
- **Calibration**: nếu nhóm tự-duyệt (need_review=false) có field SAI → ngưỡng/công thức
  confidence chưa đạt. Nâng `min_confidence` hoặc chỉnh trọng số trong `core/confidence.py`.
- **Field yếu**: field nào accuracy thấp → sửa `mo_ta` trong `configs/*.json` (không train).

### B.6 Tắt pod (BẮT BUỘC)
```bash
# từ Mac kéo kết quả về: rsync -avz root@<pod>:/workspace/vcb-ocr/output/ ./output/
```
RunPod → Pods → **Terminate** (xoá sạch, hết phí). Lần sau tải model lại ~5 phút.

---

## C. Vòng lặp cải thiện (thứ tự chi phí tăng dần)

1. **Nâng độ phân giải** (DPI/MAX_SIDE) — thường ăn ngay vài %.
2. **Sửa `mo_ta` field** trong cấu hình — miễn phí, điểm mạnh config-driven.
3. **Bật/tắt `use_ocr_hint`** theo field (số/mã bật, viết tay tắt) — đo A/B.
4. **Đổi recognizer OCR sang VietOCR** (tiếng Việt) nếu phân loại/đối chiếu sai do lột dấu.
5. **Model to hơn**: Qwen2.5-VL-32B-AWQ (GPU 48GB).
6. **Pipeline 2 bước cho bảng (BCTC)**: transcriber → LLM text-only.
7. **Fine-tune LoRA** trên log chỉnh sửa của người hậu kiểm.

---

## D. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `exceeds context size (4096)` | Ollama context nhỏ | `MAX_SIDE=1024` + `OLLAMA_CONTEXT_LENGTH=8192` |
| Mọi field `need_review`, conf thấp | Ollama không trả logprobs | Bình thường ở dev; lên GPU/vLLM sẽ có logprobs |
| `LỖI VLM 400/404` | sai `OCR_MODEL`/`OCR_BASE_URL` | kiểm tra `curl <BASE_URL>/models` |
| Trang thành `unknown` | định danh không khớp (lột dấu) | `classify.py` đã khớp bỏ dấu; kiểm tra `identifier.fields` trong config |
| `bbox: null` nhiều | value không khớp OCR (chữ Việt lột dấu) | dùng VietOCR rec, hoặc chấp nhận (bbox chỉ tô khi khớp ≥0.6) |
| vLLM OOM | VRAM thiếu | giảm `max-model-len`, bản AWQ, hoặc GPU lớn hơn |
