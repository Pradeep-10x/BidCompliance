"""
OCR Service — Dual-Path Document Text Extraction Pipeline.

Architecture (aligned to PRD §11.1):
    1. Digital PDF fast-path:   PyMuPDF text extraction (~20ms per page)
    2. Scanned/Image fallback:  OpenCV pre-processing → Tesseract OCR

Pre-processing pipeline for scanned documents:
    - Grayscale conversion
    - Otsu binary thresholding (removes watermarks, colored backgrounds)
    - Optional deskew via minAreaRect rotation
    - DPI normalization hint to Tesseract

Output contract:
    - Page-wise text strings
    - Word-level bounding boxes (for evidence provenance per PRD §5.2)
    - Extraction method tag (digital_vector | ocr_preprocessed | ocr_raw)
"""

import os
import shutil
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional
from PIL import Image, UnidentifiedImageError
import pytesseract
import numpy as np

from shared.exceptions import (
    OCREngineNotFoundError,
    OCRExecutionError,
    CorruptedDocumentError,
)

logger = logging.getLogger("ml_services.ocr")

# ─────────────────────────────────────────────────────────────────────
# Tesseract Configuration
# ─────────────────────────────────────────────────────────────────────
DEFAULT_WIN_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if not shutil.which("tesseract") and DEFAULT_WIN_TESSERACT.exists():
    pytesseract.pytesseract.tesseract_cmd = str(DEFAULT_WIN_TESSERACT)

# Tesseract config: treat as a single block of text, use eng, apply DPI hint
TESSERACT_CONFIG = "--oem 3 --psm 6 -l eng --dpi 300"

# Minimum characters for a PDF page to be considered digitally-generated
# (vs. a scanned/image-only page)
DIGITAL_TEXT_MIN_CHARS = 50


# ─────────────────────────────────────────────────────────────────────
# Image Pre-Processing (OpenCV)
# ─────────────────────────────────────────────────────────────────────

def _try_import_cv2():
    """Lazy import OpenCV — gracefully degrade if not installed."""
    try:
        import cv2
        return cv2
    except ImportError:
        logger.warning("opencv-python-headless not installed. Image pre-processing disabled.")
        return None


def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """Apply Indian government document-specific pre-processing.

    Pipeline:
        1. Convert to grayscale
        2. Otsu binary thresholding (removes watermarks, Ashoka emblem, stamps)
        3. Morphological noise removal (optional small kernel open)
        4. Return cleaned binary image

    Falls back to original image if OpenCV is unavailable.
    """
    cv2 = _try_import_cv2()
    if cv2 is None:
        return pil_image.convert("L")  # At minimum, convert to grayscale

    try:
        # PIL → numpy → OpenCV
        img_array = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Otsu thresholding — automatically finds optimal threshold
        # This removes colored backgrounds, watermarks, and light stamps
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological opening to remove small noise specks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        return Image.fromarray(cleaned)

    except Exception as e:
        logger.warning("Image pre-processing failed (%s), using grayscale fallback.", e)
        return pil_image.convert("L")


def deskew_image(pil_image: Image.Image) -> Image.Image:
    """Deskew a scanned document image using minimum area rectangle rotation.

    Only applies rotation if the detected skew angle is between 0.5° and 15°.
    Falls back to original if OpenCV is unavailable or deskew fails.
    """
    cv2 = _try_import_cv2()
    if cv2 is None:
        return pil_image

    try:
        img_array = np.array(pil_image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Find text coordinates
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 100:
            return pil_image  # Not enough dark pixels to estimate angle

        angle = cv2.minAreaRect(coords)[-1]

        # Normalize angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Only deskew if angle is meaningful but not extreme
        if abs(angle) < 0.5 or abs(angle) > 15:
            return pil_image

        h, w = img_array.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img_array, matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return Image.fromarray(rotated)

    except Exception as e:
        logger.warning("Deskew failed (%s), using original image.", e)
        return pil_image


# ─────────────────────────────────────────────────────────────────────
# PyMuPDF Digital PDF Extraction
# ─────────────────────────────────────────────────────────────────────

def _try_import_fitz():
    """Lazy import PyMuPDF (fitz) — gracefully degrade if not installed."""
    try:
        import fitz
        return fitz
    except ImportError:
        logger.warning("PyMuPDF not installed. Digital PDF fast-path disabled.")
        return None


def extract_from_digital_pdf(file_path: str) -> Optional[dict]:
    """Extract text and word-level data from a digital (vector) PDF using PyMuPDF.

    Returns None if PyMuPDF is not installed or if the PDF is a scan.

    Returns dict with:
        - page_texts: list[str]
        - word_data: list[dict] with text, bbox, confidence, page
        - method: "digital_vector"
    """
    fitz = _try_import_fitz()
    if fitz is None:
        return None

    ext = Path(file_path).suffix.lower()
    if ext != ".pdf":
        return None

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.warning("PyMuPDF could not open '%s': %s", file_path, e)
        return None

    page_texts = []
    word_data = []
    all_digital = True

    for page_idx, page in enumerate(doc, start=1):
        text = page.get_text("text")

        if len(text.strip()) >= DIGITAL_TEXT_MIN_CHARS:
            page_texts.append(text)

            # Extract word-level data with bounding boxes
            words_on_page = page.get_text("words")
            for block in words_on_page:
                x0, y0, x1, y1, word_text, block_no, line_no, word_no = block
                if word_text.strip():
                    word_data.append({
                        "text": word_text.strip(),
                        "bbox": [int(x0), int(y0), int(x1), int(y1)],
                        "confidence": 1.0,  # Digital extraction = perfect confidence
                        "page": page_idx,
                    })
        else:
            all_digital = False
            break  # If any page is a scan, fall back to OCR for the whole doc

    doc.close()

    if not all_digital or not page_texts:
        return None  # Contains scanned pages — fallback to OCR

    return {
        "page_texts": page_texts,
        "word_data": word_data,
        "method": "digital_vector",
    }


def extract_from_digital_pdf_bytes(file_bytes: bytes) -> Optional[dict]:
    """Extract text from digital PDF bytes using PyMuPDF.

    Same as extract_from_digital_pdf but accepts raw bytes.
    """
    fitz = _try_import_fitz()
    if fitz is None:
        return None

    if not file_bytes or file_bytes[:5] != b"%PDF-":
        return None

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        logger.warning("PyMuPDF could not open byte stream: %s", e)
        return None

    page_texts = []
    word_data = []
    all_digital = True

    for page_idx, page in enumerate(doc, start=1):
        text = page.get_text("text")

        if len(text.strip()) >= DIGITAL_TEXT_MIN_CHARS:
            page_texts.append(text)

            words_on_page = page.get_text("words")
            for block in words_on_page:
                x0, y0, x1, y1, word_text, block_no, line_no, word_no = block
                if word_text.strip():
                    word_data.append({
                        "text": word_text.strip(),
                        "bbox": [int(x0), int(y0), int(x1), int(y1)],
                        "confidence": 1.0,
                        "page": page_idx,
                    })
        else:
            all_digital = False
            break

    doc.close()

    if not all_digital or not page_texts:
        return None

    return {
        "page_texts": page_texts,
        "word_data": word_data,
        "method": "digital_vector",
    }


# ─────────────────────────────────────────────────────────────────────
# Tesseract OCR (with pre-processing)
# ─────────────────────────────────────────────────────────────────────

def is_tesseract_available() -> bool:
    """Returns True if the Tesseract executable is installed and runnable."""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _image_pages_from_path(path: str) -> list[Image.Image]:
    """Return a list of Pillow Image objects, one per page.

    Supports PDF via PyMuPDF rasterization (preferred) or pdf2image fallback.
    """
    ext = Path(path).suffix.lower()
    if ext != ".pdf":
        return [Image.open(path)]

    # Try PyMuPDF rasterization first (no poppler dependency)
    fitz = _try_import_fitz()
    if fitz is not None:
        try:
            doc = fitz.open(path)
            images = []
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            doc.close()
            return images
        except Exception as e:
            logger.warning("PyMuPDF rasterization failed: %s. Trying pdf2image.", e)

    # Fallback to pdf2image (requires poppler)
    try:
        from pdf2image import convert_from_path
        return convert_from_path(path, dpi=300)
    except ImportError:
        raise RuntimeError(
            "Neither PyMuPDF nor pdf2image is available for PDF rasterization. "
            "Install at least one: pip install PyMuPDF or pip install pdf2image"
        )


def _image_pages_from_bytes(file_bytes: bytes) -> list[Image.Image]:
    """Return a list of Pillow Image objects from raw bytes."""
    if file_bytes[:5] == b"%PDF-":
        fitz = _try_import_fitz()
        if fitz is not None:
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                images = []
                for page in doc:
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    images.append(img)
                doc.close()
                return images
            except Exception as e:
                logger.warning("PyMuPDF bytes rasterization failed: %s", e)

        try:
            from pdf2image import convert_from_bytes
            return convert_from_bytes(file_bytes, dpi=300)
        except ImportError:
            raise RuntimeError("No PDF rasterization library available for byte streams.")

    return [Image.open(BytesIO(file_bytes))]


def run_ocr(image_path: str) -> str:
    """Takes a path to a document image and returns the raw text found in it.

    Applies pre-processing pipeline before Tesseract OCR.
    """
    try:
        image = Image.open(image_path)
    except (UnidentifiedImageError, OSError) as e:
        raise CorruptedDocumentError(f"Cannot open image file '{image_path}': {str(e)}")

    try:
        # Pre-process: deskew → grayscale/threshold
        image = deskew_image(image)
        image = preprocess_image_for_ocr(image)
        text = pytesseract.image_to_string(image, config=TESSERACT_CONFIG)
        return text
    except pytesseract.TesseractNotFoundError:
        raise OCREngineNotFoundError()
    except pytesseract.TesseractError as e:
        raise OCRExecutionError(str(e))
    except Exception as e:
        raise OCRExecutionError(f"Unexpected error during OCR: {str(e)}")


def run_ocr_from_bytes(image_bytes: bytes) -> str:
    """Takes raw image bytes and returns the raw text found in it.

    For PDFs: tries digital extraction first, then falls back to OCR.
    For images: applies pre-processing pipeline.
    """
    if not image_bytes:
        raise CorruptedDocumentError("Received empty image byte stream.")

    # PDF: try digital extraction first
    if image_bytes[:5] == b"%PDF-":
        result = extract_from_digital_pdf_bytes(image_bytes)
        if result:
            return "\n\n".join(result["page_texts"])

    # Image or scanned PDF
    try:
        if image_bytes[:5] == b"%PDF-":
            pages = _image_pages_from_bytes(image_bytes)
            texts = []
            for page_img in pages:
                page_img = deskew_image(page_img)
                page_img = preprocess_image_for_ocr(page_img)
                texts.append(pytesseract.image_to_string(page_img, config=TESSERACT_CONFIG))
            return "\n\n".join(texts)

        image = Image.open(BytesIO(image_bytes))
        image = deskew_image(image)
        image = preprocess_image_for_ocr(image)
        text = pytesseract.image_to_string(image, config=TESSERACT_CONFIG)
        return text
    except (UnidentifiedImageError, OSError) as e:
        raise CorruptedDocumentError(f"Cannot decode image stream: {str(e)}")
    except pytesseract.TesseractNotFoundError:
        raise OCREngineNotFoundError()
    except pytesseract.TesseractError as e:
        raise OCRExecutionError(str(e))
    except Exception as e:
        raise OCRExecutionError(f"Unexpected error during OCR: {str(e)}")


def run_ocr_multi(image_path: str) -> list[str]:
    """Run OCR on each page of image_path and return a list of page-wise text strings.

    For PDFs: tries digital extraction first (instant, perfect quality).
    For scanned/image PDFs: applies pre-processing before Tesseract.
    """
    # Try digital PDF extraction first
    digital_result = extract_from_digital_pdf(image_path)
    if digital_result:
        logger.info("Digital PDF fast-path: extracted %d pages in vector mode.",
                     len(digital_result["page_texts"]))
        return digital_result["page_texts"]

    # Fallback: rasterize + pre-process + OCR
    pages = _image_pages_from_path(image_path)
    page_texts = []
    for img in pages:
        img = deskew_image(img)
        img = preprocess_image_for_ocr(img)
        page_texts.append(pytesseract.image_to_string(img, config=TESSERACT_CONFIG))
    return page_texts


def extract_word_data_multi(image_path: str) -> list[dict]:
    """Extract word-level OCR data for all pages of image_path.

    Returns a list of dictionaries with keys: text, bbox ([x1, y1, x2, y2]),
    confidence (0-1), and page (1-based).

    For digital PDFs, returns PyMuPDF word positions (confidence=1.0).
    For scanned docs, returns Tesseract word-level data with pre-processing.
    """
    # Try digital PDF extraction first (perfect bounding boxes from vector)
    digital_result = extract_from_digital_pdf(image_path)
    if digital_result:
        logger.info("Word data: digital fast-path for %d pages.", len(digital_result["page_texts"]))
        return digital_result["word_data"]

    # Fallback: Tesseract word-level extraction with pre-processing
    pages = _image_pages_from_path(image_path)
    words: list[dict] = []
    for page_idx, img in enumerate(pages, start=1):
        # Pre-process before word-level extraction
        img = deskew_image(img)
        img = preprocess_image_for_ocr(img)

        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=TESSERACT_CONFIG)
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
                "confidence": round(conf, 3),
                "page": page_idx,
            })
    return words


def find_phrase_box(words: list[dict], phrase: str, page: Optional[int] = None) -> Optional[dict]:
    """Find the bounding box that encloses a phrase in the OCR word list.

    The search is case-insensitive and matches consecutive words.

    Args:
        words: Word-level data from extract_word_data_multi
        phrase: The text phrase to locate
        page: Optional page number to restrict search to

    Returns:
        dict with bbox [x1, y1, x2, y2] and page, or None if not found.
    """
    tokens = [t.lower() for t in phrase.split() if t]
    if not tokens:
        return None

    search_words = words
    if page is not None:
        search_words = [w for w in words if w["page"] == page]

    for i in range(len(search_words)):
        if search_words[i]["text"].lower() != tokens[0]:
            continue
        j = i
        match = True
        for token in tokens:
            if j >= len(search_words) or search_words[j]["text"].lower() != token:
                match = False
                break
            j += 1
        if match:
            xs = [search_words[k]["bbox"][0] for k in range(i, j)]
            ys = [search_words[k]["bbox"][1] for k in range(i, j)]
            xe = [search_words[k]["bbox"][2] for k in range(i, j)]
            ye = [search_words[k]["bbox"][3] for k in range(i, j)]
            return {
                "bbox": [min(xs), min(ys), max(xe), max(ye)],
                "page": search_words[i]["page"],
            }
    return None
