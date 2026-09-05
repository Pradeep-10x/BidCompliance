from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
import random


def augment_image(src: Path, dst: Path, kind: str):
    im = Image.open(src).convert("RGB")
    if kind == "blur":
        out = im.filter(ImageFilter.GaussianBlur(radius=1.4))
    elif kind == "rotate":
        out = im.rotate(random.choice([-2,-1,1,2]), expand=False, fillcolor="white")
    elif kind == "low_contrast":
        out = ImageEnhance.Contrast(im).enhance(0.70)
    elif kind == "low_resolution":
        small = im.resize((620,877), Image.Resampling.BILINEAR)
        out = small.resize((1240,1754), Image.Resampling.BILINEAR)
    else:
        raise ValueError(f"Unknown augmentation: {kind}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, format="PNG")
