# Synthetic Document Dataset Generator

A beginner-friendly Python project for generating clearly fictional document images and ground-truth JSON metadata for OCR/document-AI research.

## Included document types

- BIS-style product certification
- PAN-style identity card
- MCA-style certificate of incorporation
- GST-style tax registration
- DPIIT-style startup recognition
- Udyam-style enterprise registration

The layouts are inspired by the **field structure** of the supplied reference documents, but they intentionally use fictional branding and non-authentic security elements.

## Safety

Every generated document contains **SYNTHETIC / DEMO / NOT VALID**.

The generator does not create official government logos, seals, signatures, scannable QR codes, or valid government identifiers. Identifiers use explicit synthetic forms such as `SYN-BIS-000001`.

## Install

```bash
python -m pip install -r requirements.txt
```

## Generate a small test set

```bash
python run_generation.py --count-per-type 2 --augment --reset
```

## Generate a larger submission dataset

```bash
python run_generation.py --count-per-type 25 --augment --reset
```

This creates:

- 25 raw samples × 6 document types = 150 raw images
- 4 augmented versions per raw image = 600 augmented images
- 750 image files total
- one ground-truth JSON per raw document
- one CSV manifest covering raw and augmented images
- deterministic 70/15/15 train/validation/test split per document type

## Output structure

```text
synthetic_doc_dataset/
├── raw/<type>/images/
├── augmented/<type>/images/
├── annotations/<type>/
├── splits/
├── dataset_manifest.csv
└── README.md
```

## What the main Python files do

- `generator/schemas.py` — document field definitions
- `generator/field_generators.py` — synthetic names, companies, addresses, dates, etc.
- `generator/id_generator.py` — safe synthetic identifiers
- `generator/record_builder.py` — creates one complete document record
- `generator/json_writer.py` — saves common + document-specific ground truth
- `generator/renderer.py` — renders all six safe layouts with Pillow
- `generator/augmentor.py` — blur, rotate, low contrast and low resolution variants
- `generator/manifest_writer.py` — writes dataset metadata to CSV
- `generator/splitter.py` — deterministic train/validation/test assignment
- `run_generation.py` — main entry point
