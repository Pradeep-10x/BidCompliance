import pytesseract
from PIL import Image

# --- Windows-only setup ---
# If Tesseract isn't on your system PATH, uncomment and set the correct path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def run_ocr(image_path: str) -> str:
    """
    Takes a path to a document image and returns the raw text found in it.
    """
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text


def run_ocr_from_bytes(image_bytes: bytes) -> str:
    """
    Same as run_ocr, but takes raw image bytes instead of a file path.
    Use this version once the backend is sending uploaded files directly
    (rather than a path on disk).
    """
    from io import BytesIO
    image = Image.open(BytesIO(image_bytes))
    return pytesseract.image_to_string(image)
