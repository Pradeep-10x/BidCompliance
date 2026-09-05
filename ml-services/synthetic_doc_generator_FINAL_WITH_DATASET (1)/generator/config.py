from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "synthetic_doc_dataset"
WATERMARK = "SYNTHETIC / DEMO / NOT VALID"
CANVAS_SIZE = (1240, 1754)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]
BOLD_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
DOC_TYPES = ("bis", "pan", "mca", "gst", "dpiit", "udyam")
SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
