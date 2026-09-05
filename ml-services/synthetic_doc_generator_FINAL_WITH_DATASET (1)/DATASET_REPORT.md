# Dataset / MVP Report

## Objective

Generate a privacy-safe synthetic corpus for document OCR and information extraction experiments.

## Document classes

BIS, PAN, MCA, GST, DPIIT, UDYAM.

## Ground truth

Each raw document has a JSON annotation containing the common normalized structure plus the exact document-specific fields used to render the image.

## Image variations

Raw clean image plus four optional augmentations:

- Gaussian blur
- small rotation
- low contrast
- low resolution then upscaling

## Split policy

Raw documents are assigned deterministically 70% train, 15% validation and 15% test within each document type. Augmented variants inherit the parent document's split to avoid data leakage.

## Safety

All generated outputs are explicitly synthetic and non-valid. No official government branding, authentic signatures, seals or scannable QR codes are produced.
