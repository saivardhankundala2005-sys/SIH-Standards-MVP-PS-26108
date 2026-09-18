"""
Extracts text from a standard's PDF. Falls back to OCR for scanned pages.
Also tries to pull a "normative references" section, which is how we build
the allied-standards graph later.
"""
import re
from pathlib import Path
from typing import List

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

NORMATIVE_SECTION_HEADERS = [
    "normative references", "reference", "referred indian standards",
    "indian standards referred",
]

IS_NUMBER_PATTERN = re.compile(r"IS[\s:]?\d{2,6}(?:[\s:\-]\d{1,4})?", re.IGNORECASE)


def extract_text_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        print(f"[warn] pdfplumber extraction notice: {e}")
        return ""


def extract_text_pypdf_fallback(path: Path) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def ocr_page_fallback(path: Path) -> str:
    """Only invoked when normal extraction yields near-empty text (scanned PDF)."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return ""
    images = convert_from_path(str(path))
    return "\n".join(pytesseract.image_to_string(img) for img in images)


def extract_text(path: Path) -> tuple[str, float]:
    """Returns (text, ocr_confidence). ocr_confidence=1.0 means native text
    extraction worked fine; lower values flag that OCR was needed."""
    text = extract_text_pdfplumber(path)
    if len(text.strip()) < 200:
        text = extract_text_pypdf_fallback(path)
    if len(text.strip()) < 200:
        ocr_text = ocr_page_fallback(path)
        if len(ocr_text.strip()) > len(text.strip()):
            return ocr_text, 0.6  # OCR'd — flag lower confidence
    return text, 1.0


def extract_normative_references(full_text: str) -> List[str]:
    """Finds the 'Normative References' section and pulls out IS numbers
    mentioned there, used to build the allied-standards graph."""
    lower = full_text.lower()
    start_idx = -1
    for header in NORMATIVE_SECTION_HEADERS:
        idx = lower.find(header)
        if idx != -1:
            start_idx = idx
            break
    if start_idx == -1:
        # No dedicated section found — fall back to scanning the whole doc,
        # which over-recalls but ensures we don't miss references entirely.
        section_text = full_text
    else:
        # Grab ~3000 chars after the header, which normally covers the list.
        section_text = full_text[start_idx:start_idx + 3000]

    matches = {m.group().upper().replace(" ", "") for m in IS_NUMBER_PATTERN.finditer(section_text)}
    return sorted(matches)
