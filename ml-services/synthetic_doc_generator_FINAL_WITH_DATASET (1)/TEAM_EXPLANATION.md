# Team Explanation (Very Simple)

Our project is a **synthetic document dataset generator** for OCR/document-AI research.

It takes six document classes (BIS, PAN, MCA, GST, DPIIT and Udyam), generates fictional field values, stores the exact ground truth in JSON, renders a safe synthetic document image, and records metadata in a CSV manifest.

The generated images can also be augmented with blur, rotation, low contrast and low resolution to simulate imperfect scans.

### Pipeline

`Schema → Synthetic Data → JSON Ground Truth + Document Image → Augmentation → Dataset Manifest → Train/Validation/Test`

### Safety

Every generated document is marked **SYNTHETIC / DEMO / NOT VALID**. No official government branding, authentic signatures, seals, scannable QR codes or valid government identifiers are produced.
