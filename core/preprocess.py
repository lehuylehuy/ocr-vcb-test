"""Bước 1 — Preprocess: PDF/ảnh → danh sách ảnh từng trang đã chuẩn hoá.

Đầu vào: đường dẫn PDF hoặc ảnh.
Đầu ra:  [(page_no, PIL.Image), ...]
"""
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageOps


def load_pages(path: Path, dpi: int = 250, max_side: int = 2048):
    """Render từng trang thành ảnh RGB, thu nhỏ để VLM xử lý nhanh mà vẫn đủ nét."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        pdf = pdfium.PdfDocument(str(path))
        for i, page in enumerate(pdf):
            img = page.render(scale=dpi / 72).to_pil().convert("RGB")
            img.thumbnail((max_side, max_side))       # giữ tỷ lệ
            yield i + 1, img
    else:                                              # ảnh đơn (jpg/png/webp/tiff)
        img = Image.open(path)
        # Áp hướng EXIF: ảnh chụp điện thoại lưu pixel nghiêng + cờ xoay. Không áp thì
        # model nhìn ảnh nằm ngang/dọc sai → đọc thiếu field (đặc biệt chuỗi dài tiếng Việt).
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((max_side, max_side))
        yield 1, img
