import csv
from pathlib import Path

FIELDS = ["document_id","source_id","document_type","split","is_augmented","augmentation_type","image_path","annotation_path","image_width","image_height","watermark_tag","created_date"]


def append_row(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
