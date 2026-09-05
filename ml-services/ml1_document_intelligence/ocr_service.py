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
