import os
from io import BytesIO
from pathlib import Path
from typing import Optional
from PIL import Image, UnidentifiedImageError

from .exceptions import (
    DocumentNotFoundError,
    InvalidPathError,
    EmptyDocumentError,
    InvalidDocumentFormatError,
    CorruptedDocumentError,
    FileTooLargeError,
)

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
DEFAULT_MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


def validate_image_path(image_path: str) -> Path:
    """
    Validates that a local file path points to an existing, readable,
    and uncorrupted image file.

    Raises domain exceptions if validation fails.
    """
    if not image_path or not isinstance(image_path, str) or not image_path.strip():
        raise InvalidPathError("Image path cannot be empty", str(image_path))

    path = Path(image_path.strip())

    if not path.exists():
        raise DocumentNotFoundError(str(path))

    if not path.is_file():
        raise InvalidPathError(f"Specified path is a directory, not a file: '{path}'", str(path))

    if not os.access(path, os.R_OK):
        raise InvalidPathError(f"Permission denied: cannot read file at '{path}'", str(path))

    if path.stat().st_size == 0:
        raise EmptyDocumentError(str(path))

    ext = path.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise InvalidDocumentFormatError(ext or "[no extension]", sorted(list(ALLOWED_IMAGE_EXTENSIONS)))

    # Verify image integrity with PIL
    try:
        with Image.open(path) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise CorruptedDocumentError(f"Cannot identify or decode image file '{path.name}': {str(e)}")
    except Exception as e:
        raise CorruptedDocumentError(f"Error reading image file '{path.name}': {str(e)}")

    return path


def validate_image_bytes(
    image_bytes: bytes,
    filename: Optional[str] = None,
    max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> None:
    """
    Validates raw uploaded bytes: checks size, non-emptiness, extension (if given),
    and validates header integrity with PIL.
    """
    if not image_bytes or len(image_bytes) == 0:
        raise EmptyDocumentError(filename or "upload_stream")

    if len(image_bytes) > max_bytes:
        raise FileTooLargeError(len(image_bytes), max_bytes)

    if filename:
        path = Path(filename)
        ext = path.suffix.lower()
        if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise InvalidDocumentFormatError(ext, sorted(list(ALLOWED_IMAGE_EXTENSIONS)))

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        name = filename or "uploaded_stream"
        raise CorruptedDocumentError(f"Cannot identify or decode image file '{name}': {str(e)}")
    except Exception as e:
        name = filename or "uploaded_stream"
        raise CorruptedDocumentError(f"Error reading image stream '{name}': {str(e)}")
