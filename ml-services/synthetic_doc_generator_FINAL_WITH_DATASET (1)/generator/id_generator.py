from pathlib import Path
import re

_counters = {}


def _next_serial(doc_code: str, root: Path) -> int:
    doc_dir = root / "raw" / doc_code / "images"
    max_seen = 0
    if doc_dir.exists():
        pattern = re.compile(rf"^SYN-{re.escape(doc_code.upper())}-(\d{{6}})\.png$")
        for p in doc_dir.glob("*.png"):
            m = pattern.match(p.name)
            if m:
                max_seen = max(max_seen, int(m.group(1)))
    current = max(_counters.get(doc_code, 0), max_seen) + 1
    _counters[doc_code] = current
    return current


def generate_document_id(doc_code: str, root: Path) -> str:
    return f"SYN-{doc_code.upper()}-{_next_serial(doc_code, root):06d}"


def generate_synthetic_ref(kind: str, serial: int) -> str:
    return f"SYN-{kind.upper()}-{serial:06d}"
