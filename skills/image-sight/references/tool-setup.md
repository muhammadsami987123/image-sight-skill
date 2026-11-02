# Tool Setup and Troubleshooting

Read this when `inspect_image.py` reports an unavailable tool, or when OCR quality is poor.

## Contents
1. Installing the OCR stack
2. Optional captioning models
3. External vision APIs (last resort)
4. Troubleshooting poor OCR
5. Tesseract page segmentation modes

## 1. Installing the OCR stack

Minimum (covers most documents and screenshots):

```bash
pip install pillow pytesseract --break-system-packages
apt-get install -y tesseract-ocr          # Debian/Ubuntu
# macOS: brew install tesseract
# Windows: install the UB-Mannheim build, then add it to PATH
```

Extra language packs (Tesseract codes, combine with `+`):

```bash
apt-get install -y tesseract-ocr-urd tesseract-ocr-ara tesseract-ocr-hin
python scripts/inspect_image.py page.png --mode text --lang eng+urd
```

Stronger fallback for stylized fonts, photos of signs, and many scripts (heavier, downloads models):

```bash
pip install easyocr --break-system-packages
```

If the sandbox has no network or no permission to install, report which tool is missing and what the user can run locally. Do not pretend the step succeeded.

## 2. Optional captioning models

Captioning gives a one-sentence scene description. It is useful for photos, weak for detail.

```bash
pip install transformers torch --break-system-packages
python scripts/inspect_image.py photo.jpg --mode describe
```

Notes:
- First run downloads the BLIP model (hundreds of MB). Warn the user if time matters.
- Captions are generic ("a man sitting at a desk with a laptop"). Never present them as complete descriptions.
- For object lists, an object-detection model (for example DETR via `transformers`) can be added the same way, but only when the user needs counts or locations.

## 3. External vision APIs (last resort)

If local tools cannot answer the question and the user has a vision-capable model or API available, suggest routing the image there and say why (for example: "this is a photograph where layout and visual detail matter, which OCR cannot capture"). Only call an external service if the user has configured it and consents to the image leaving their machine, since images may hold sensitive data.

## 4. Troubleshooting poor OCR

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Empty output | No text, or very low contrast | Try `--mode text`; check `colors.tone`; try inverted variant (script does this) |
| Random symbols | Wrong language, or non-text image | Set `--lang`; confirm image actually contains text |
| Missing small text | Resolution too low | Script upscales 2x; ask for a higher-resolution original if still missing |
| Columns merged into one stream | Wrong layout mode | Try `--psm 1` or `--psm 4`; use `text_reading_order` |
| Table cells misaligned | Layout lost in plain text | Rebuild rows from `boxes` y-coordinates; see the receipts and tables playbook |
| Digits misread (0/O, 1/l, 5/S) | Font or noise | Cross-check arithmetic; flag suspicious tokens |
| Skewed or rotated page | Photo taken at an angle | Rotate with Pillow using EXIF orientation or try 90, 180, 270 degree rotations and keep the best-scoring result |
| Handwriting garbled | Tesseract is weak on handwriting | Say so plainly; try `easyocr`; offer a partial transcript marked uncertain |
| Dark background, light text | Inverted polarity | Script tries inversion; confirm with `mean_brightness` |

Rotation retry snippet:

```python
from PIL import Image
import pytesseract
img = Image.open("scan.jpg")
best = max(((a, len(pytesseract.image_to_string(img.rotate(a, expand=True)).split())) for a in (0, 90, 180, 270)),
           key=lambda t: t[1])
print("best rotation:", best)
```

## 5. Tesseract page segmentation modes (`--psm`)

| PSM | Meaning | Use for |
|-----|---------|---------|
| 3 | Fully automatic (default) | Most pages |
| 4 | Single column of variable-size text | Receipts, narrow columns |
| 6 | Single uniform block | Clean paragraph or code screenshot |
| 7 | Single text line | Captions, labels, cropped lines |
| 8 | Single word | Cropped words |
| 11 | Sparse text, no order | Charts, posters, scattered labels |
| 12 | Sparse text with orientation detection | Mixed scattered text, rotated |
