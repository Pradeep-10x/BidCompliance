from typing import Any, Optional


class MLServiceException(Exception):
    """Base exception for all ML Services domain errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "ML_SERVICE_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


# --- Client-Side Errors (4xx) ---

class DocumentNotFoundError(MLServiceException):
    """Raised when a requested document path does not exist on the filesystem."""

    def __init__(self, path: str):
        super().__init__(
            message=f"Document file does not exist at specified path: '{path}'",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=404,
            details={"path": path},
        )


class InvalidPathError(MLServiceException):
    """Raised when a path is a directory or process lacks read permissions."""

    def __init__(self, message: str, path: str):
        super().__init__(
            message=message,
            error_code="INVALID_PATH",
            status_code=400,
            details={"path": path},
        )


class EmptyDocumentError(MLServiceException):
    """Raised when the document file is 0 bytes."""

    def __init__(self, path: str):
        super().__init__(
            message=f"Document file is empty (0 bytes): '{path}'",
            error_code="EMPTY_DOCUMENT",
            status_code=400,
            details={"path": path},
        )


class InvalidDocumentFormatError(MLServiceException):
    """Raised when file extension or MIME type is not a supported format."""

    def __init__(self, extension: str, supported_formats: list):
        super().__init__(
            message=f"Unsupported document format '{extension}'. Supported formats: {', '.join(supported_formats)}",
            error_code="INVALID_DOCUMENT_FORMAT",
            status_code=400,
            details={"extension": extension, "supported_formats": supported_formats},
        )


class CorruptedDocumentError(MLServiceException):
    """Raised when image decoding fails or file is corrupted."""

    def __init__(self, message: str = "Document image is corrupted or could not be decoded."):
        super().__init__(
            message=message,
            error_code="CORRUPTED_DOCUMENT",
            status_code=400,
        )


class FileTooLargeError(MLServiceException):
    """Raised when uploaded file exceeds the maximum allowed size."""

    def __init__(self, size_bytes: int, max_bytes: int):
        max_mb = max_bytes / (1024 * 1024)
        size_mb = size_bytes / (1024 * 1024)
        super().__init__(
            message=f"Uploaded file ({size_mb:.2f} MB) exceeds maximum allowed size ({max_mb:.1f} MB)",
            error_code="FILE_TOO_LARGE",
            status_code=413,
            details={"size_bytes": size_bytes, "max_bytes": max_bytes},
        )


# --- Server & Infrastructure Errors (5xx / 503) ---

class OCREngineNotFoundError(MLServiceException):
    """Raised when Tesseract OCR binary is missing from PATH or system."""

    def __init__(
        self,
        message: str = (
            "Tesseract OCR engine is not installed or not configured in system PATH. "
            "Please install Tesseract-OCR (e.g. from UB-Mannheim) and ensure it is accessible."
        ),
    ):
        super().__init__(
            message=message,
            error_code="OCR_ENGINE_NOT_FOUND",
            status_code=503,
            details={"engine": "tesseract", "help": "Install Tesseract-OCR and add to PATH or set tesseract_cmd"},
        )


class OCRExecutionError(MLServiceException):
    """Raised when OCR engine crashes or exits with an error."""

    def __init__(self, message: str):
        super().__init__(
            message=f"OCR execution failure: {message}",
            error_code="OCR_EXECUTION_ERROR",
            status_code=500,
        )


class DocumentClassificationError(MLServiceException):
    """Raised when classifier fails during inference."""

    def __init__(self, message: str):
        super().__init__(
            message=f"Document classification failure: {message}",
            error_code="CLASSIFICATION_ERROR",
            status_code=500,
        )


class FieldExtractionError(MLServiceException):
    """Raised when field extractor fails during extraction."""

    def __init__(self, doc_type: str, message: str):
        super().__init__(
            message=f"Field extraction failure for document type '{doc_type}': {message}",
            error_code="FIELD_EXTRACTION_ERROR",
            status_code=500,
            details={"document_type": doc_type},
        )
