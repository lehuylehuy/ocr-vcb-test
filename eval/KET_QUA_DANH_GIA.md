# Đánh giá OCR tiếng Việt: Tesseract vs PaddleOCR (PP-OCR/RapidOCR)

Thử nghiệm trên trang 1 sổ đỏ VCB (`data/samples/sodo_1.pdf`), render 250 DPI.
Chạy: `.venv/bin/python eval/compare_ocr.py`

## Kết quả số

| Tiêu chí | Tesseract (lang=vie) | RapidOCR / PP-OCR (mặc định) |
|---|---|---|
| Field khớp đúng | **6/7** | 5/7 |
| **Dấu tiếng Việt** | ✅ **ĐỌC ĐÚNG** | ❌ **MẤT SẠCH DẤU** |
| Số/mã (CCCD, thửa, tờ, diện tích) | tốt (trượt "316"→"3l6") | ✅ **rất tốt** (316 đúng) |
| Tách dòng/layout | trung bình, dính nhãn+giá trị | ✅ sạch (37 dòng gọn) |
| Tốc độ | 9.2s (ảnh 6205×8973) | **1.4s** (tự downscale) |
| bbox | không (image_to_string) | ✅ có, kèm conf 0.93 |

## Bằng chứng — cùng một dòng, hai engine đọc khác nhau

```
Bản gốc:    CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ... Bà: Nguyễn Thị Hương ... Hải Dương
Tesseract:  CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ... Bà: Nguyễn Thị Hương ... Hải Dương   ✅
RapidOCR:   CONG HOA XA HQI CHU NGHIA VIET NAM ... Ba: Nguyen Thi Hurong ... Hai Duong   ❌
```

## Phát hiện quyết định

**RapidOCR mặc định KHÔNG phải "PaddleOCR yếu tiếng Việt" — nó đang dùng SAI model nhận dạng.**
Bản mặc định đóng gói model recognition PP-OCRv4 tiếng Trung+Latin, **không có bảng ký tự
tiếng Việt** → mọi chữ có dấu bị lột dấu. Đây đúng là bài học kiến trúc det/rec:

- **Detection** (tìm hộp chữ): RapidOCR **tốt hơn** Tesseract — tách dòng sạch, đọc "316" đúng.
- **Recognition** (đọc chữ): model mặc định **sai ngôn ngữ** → hỏng tiếng Việt.

→ Chất lượng tiếng Việt do **slot recognition** quyết định, không phải do "Paddle vs Tesseract".

## Kết luận theo VAI TRÒ trong pipeline (quan trọng)

OCR nhỏ trong hệ thống này KHÔNG phải nguồn giá trị cuối (vLLM mới là). Nó dùng cho 3 việc,
và lựa chọn engine khác nhau tuỳ việc:

| Dùng để | Cần dấu TV? | Engine phù hợp |
|---|---|---|
| **Khớp trường định danh** (phân loại trang) | có ("Thửa đất số"...) | Tesseract vie, HOẶC RapidOCR + **khớp bỏ dấu** |
| **bbox** để khoanh vùng hậu kiểm | không | ✅ RapidOCR (detection sạch, nhanh, có bbox) |
| **Đối chiếu confidence** field số/mã | không | ✅ RapidOCR (số chính xác) |
| Đối chiếu confidence field chữ TV | có | cần recognizer tiếng Việt |

## Khuyến nghị

1. **Không dùng RapidOCR mặc định làm nguồn text tiếng Việt.** Với việc phân loại trang,
   hoặc bật **khớp bỏ dấu** (`unidecode`), hoặc thay recognizer.
2. **Combo tối ưu = detection của PP-OCR + recognition tiếng Việt**:
   - `PP-OCRv5 det` (hoặc RapidOCR det) cho bbox + tách dòng
   - `VietOCR` (pbcquoc) hoặc PP-OCRv5 rec bản Việt cho đọc chữ có dấu
   Đây là combo cần validate ở bước tiếp theo.
3. **Tesseract vie** đủ tốt làm baseline nhanh (đặc biệt cho phân loại), nhưng chậm trên
   ảnh lớn và tách layout kém hơn — cần crop/giảm DPI.
4. Với **field số/mã** (CCCD, số thửa) RapidOCR đối chiếu tốt hơn Tesseract — dùng đúng chỗ.

## Việc tiếp theo để đánh giá đầy đủ
- [ ] Thử RapidOCR/PP-OCR với **recognizer tiếng Việt** (VietOCR hoặc PP-OCRv5 vi)
- [ ] Thử EasyOCR `vi` làm điểm tham chiếu thứ ba
- [ ] Đo trên chữ **viết tay** (ngày cấp) — cả hai engine đều yếu ở đây
- [ ] Đo trên **bảng** (BCTC) — layout phức tạp
