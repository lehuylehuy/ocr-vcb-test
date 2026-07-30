"""Đọc cấu hình runtime từ .env — nơi duy nhất quyết định pipeline nói chuyện với model nào."""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("OCR_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("OCR_MODEL", "qwen2.5vl:3b")
API_KEY = os.getenv("OCR_API_KEY", "dummy")

PDF_DPI = int(os.getenv("PDF_DPI", "250"))
MAX_SIDE = int(os.getenv("MAX_SIDE", "2048"))
