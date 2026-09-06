from pathlib import Path
from datetime import datetime, timezone
import argparse
import shutil
from PIL import Image

from generator.config import ROOT, DOC_TYPES, SPLIT_RATIOS
from generator.record_builder import build_record
from generator.json_writer import to_common_json, save_json
from generator.renderer import render_document
from generator.manifest_writer import append_row
from generator.splitter import SplitAssigner
from generator.augmentor import augment_image


def ensure_dirs():
    for doc in DOC_TYPES:
        (ROOT / "raw" / doc / "images").mkdir(parents=True, exist_ok=True)
        (ROOT / "augmented" / doc / "images").mkdir(parents=True, exist_ok=True)
        (ROOT / "annotations" / doc).mkdir(parents=True, exist_ok=True)
    (ROOT / "splits").mkdir(parents=True, exist_ok=True)


def reset_dataset():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ensure_dirs()


def generate(count_per_type: int, augment: bool, reset: bool = False):
    if count_per_type < 1:
        raise ValueError("count_per_type must be at least 1")
    if reset:
        reset_dataset()
    else:
        ensure_dirs()

    splitter = SplitAssigner()
    manifest = ROOT / "dataset_manifest.csv"
    augmentation_kinds = ["blur", "rotate", "low_contrast", "low_resolution"]

    for doc_type in DOC_TYPES:
        ids_for_split = {"train": [], "val": [], "test": []}
        for idx in range(count_per_type):
            record = build_record(doc_type)
            doc_id = record.document_id
            ann_path = ROOT / "annotations" / doc_type / f"{doc_id}.json"
            img_path = ROOT / "raw" / doc_type / "images" / f"{doc_id}.png"

            save_json(to_common_json(record), ann_path)
            image = render_document(record, img_path)
            split = splitter.assign_for_index(idx, count_per_type)
            ids_for_split[split].append(doc_id)
            append_row(manifest, {
                "document_id": doc_id,
                "source_id": doc_id,
                "document_type": doc_type,
                "split": split,
                "is_augmented": False,
                "augmentation_type": "",
                "image_path": str(img_path.relative_to(ROOT.parent)),
                "annotation_path": str(ann_path.relative_to(ROOT.parent)),
                "image_width": image.width,
                "image_height": image.height,
                "watermark_tag": record.watermark_tag,
                "created_date": datetime.now(timezone.utc).isoformat(),
            })

            if augment:
                for kind in augmentation_kinds:
                    aug_id = f"{doc_id}_{kind}"
                    aug_path = ROOT / "augmented" / doc_type / "images" / f"{aug_id}.png"
                    augment_image(img_path, aug_path, kind)
                    with Image.open(aug_path) as aug_image:
                        aug_w, aug_h = aug_image.size
                    append_row(manifest, {
                        "document_id": aug_id,
                        "source_id": doc_id,
                        "document_type": doc_type,
                        "split": split,
                        "is_augmented": True,
                        "augmentation_type": kind,
                        "image_path": str(aug_path.relative_to(ROOT.parent)),
                        "annotation_path": str(ann_path.relative_to(ROOT.parent)),
                        "image_width": aug_w,
                        "image_height": aug_h,
                        "watermark_tag": record.watermark_tag,
                        "created_date": datetime.now(timezone.utc).isoformat(),
                    })

        for split, ids in ids_for_split.items():
            (ROOT / "splits" / f"{doc_type}_{split}_ids.txt").write_text(
                "\n".join(ids) + ("\n" if ids else ""), encoding="utf-8"
            )

    total_raw = count_per_type * len(DOC_TYPES)
    total_aug = total_raw * len(augmentation_kinds) if augment else 0
    print(
        f"Generated {count_per_type} sample(s) per type. "
        f"Raw={total_raw}, Augmented={total_aug}. Output: {ROOT}"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate safe synthetic document-AI research data.")
    p.add_argument("--count-per-type", type=int, default=1)
    p.add_argument("--augment", action="store_true")
    p.add_argument("--reset", action="store_true", help="Delete the existing dataset before generation")
    args = p.parse_args()
    generate(args.count_per_type, args.augment, args.reset)
