import os
import shutil
from io import BytesIO
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import pytesseract

from shared.exceptions import (
    OCREngineNotFoundError,
    OCRExecutionError,
    CorruptedDocumentError,
)

# --- Windows auto-detection ---
# Check if standard Windows Tesseract path exists if not already found in PATH
DEFAULT_WIN_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if not shutil.which("tesseract") and DEFAULT_WIN_TESSERACT.exists():
    pytesseract.pytesseract.tesseract_cmd = str(DEFAULT_WIN_TESSERACT)


def is_tesseract_available() -> bool:
    """Returns True if the Tesseract executable is installed and runnable."""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def run_ocr(image_path: str) -> str:
    """
    Takes a path to a document image and returns the raw text found in it.
    Raises domain exceptions if image cannot be read or OCR fails.
    """
    try:
        image = Image.open(image_path)
    except (UnidentifiedImageError, OSError) as e:
        raise CorruptedDocumentError(f"Cannot open image file '{image_path}': {str(e)}")

    try:
        text = pytesseract.image_to_string(image)
        return text
    except pytesseract.TesseractNotFoundError:
        raise OCREngineNotFoundError()
    except pytesseract.TesseractError as e:
        raise OCRExecutionError(str(e))
    except Exception as e:
        raise OCRExecutionError(f"Unexpected error during OCR: {str(e)}")


def run_ocr_from_bytes(image_bytes: bytes) -> str:
    """
    Takes raw image bytes and returns the raw text found in it.
    Raises domain exceptions if image cannot be decoded or OCR fails.
    """
    if not image_bytes:
        raise CorruptedDocumentError("Received empty image byte stream.")

    try:
        image = Image.open(BytesIO(image_bytes))
    except (UnidentifiedImageError, OSError) as e:
        raise CorruptedDocumentError(f"Cannot decode image stream: {str(e)}")

    try:
        text = pytesseract.image_to_string(image)
        return text
    except pytesseract.TesseractNotFoundError:
        raise OCREngineNotFoundError()
    except pytesseract.TesseractError as e:
        raise OCRExecutionError(str(e))
    except Exception as e:
        raise OCRExecutionError(f"Unexpected error during OCR: {str(e)}")
def _image_pages_from_path(path: str) -> list[Image.Image]:
    """Return a list of Pillow Image objects, one per page.

    Supports PDF via ``pdf2image``; otherwise treats the file as a single image.
    """
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        try:
            from pdf2image import convert_from_path
        except ImportError as exc:
            raise RuntimeError("pdf2image is required for PDF OCR") from exc
        return convert_from_path(path)
    return [Image.open(path)]

def extract_word_data_multi(image_path: str) -> list[dict]:
    """Extract word‑level OCR data for **all** pages of *image_path*.

    Returns a list of dictionaries with keys: ``text``, ``bbox`` (``[x1, y1, x2, y2]``),
    ``confidence`` (0‑1), and ``page`` (1‑based).
    """
    pages = _image_pages_from_path(image_path)
    words: list[dict] = []
    for page_idx, img in enumerate(pages, start=1):
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        n = len(data.get("text", []))
        for i in range(n):
            txt = data["text"][i].strip()
            if not txt:
                continue
            conf_raw = data["conf"][i]
            try:
                conf = float(conf_raw) / 100.0 if conf_raw != "-1" else 0.0
            except ValueError:
                conf = 0.0
            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i],
            )
            words.append({
                "text": txt,
                "bbox": [x, y, x + w, y + h],
                "confidence": conf,
                "page": page_idx,
            })
    return words

def find_phrase_box(words: list[dict], phrase: str) -> list[int] | None:
    """Find the bounding box that encloses *phrase* in the OCR word list.

    The search is case‑insensitive and matches consecutive words.
    Returns ``[x1, y1, x2, y2]`` or ``None`` if not found.
    """
    tokens = [t.lower() for t in phrase.split() if t]
    if not tokens:
        return None
    for i in range(len(words)):
        if words[i]["text"].lower() != tokens[0]:
            continue
        j = i
        match = True
        for token in tokens:
            if j >= len(words) or words[j]["text"].lower() != token:
                match = False
                break
            j += 1
        if match:
            xs = [words[k]["bbox"][0] for k in range(i, j)]
            ys = [words[k]["bbox"][1] for k in range(i, j)]
            xe = [words[k]["bbox"][2] for k in range(i, j)]
            ye = [words[k]["bbox"][3] for k in range(i, j)]
            return [min(xs), min(ys), max(xe), max(ye)]
    return None

def run_ocr_multi(image_path: str) -> list[str]:
    """Run OCR on each page of *image_path* and return a list of page‑wise text strings."""
    pages = _image_pages_from_path(image_path)
    page_texts: list[str] = []
    for img in pages:
        page_texts.append(pytesseract.image_to_string(img))
    return page_texts
