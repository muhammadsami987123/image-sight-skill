# Complete Setup Guide — Image Sight

This guide covers everything needed to make a **text-only model** (a model with no native vision) able to "see" images using the Image Sight skill: installing the OCR stack, optional captioning, external vision APIs as a last resort, image-to-PDF conversion tools, download links, and troubleshooting.

> **Important context:** A text-only model cannot view pixels. Even small models (1B / 2B / 7B / 40B parameters) have no eyes. You do **not** need to train a custom model to read images — instead you give the model **tools** (OCR, metadata, captioning) that turn pixels into text, and the model reasons over that text. Training a vision model from scratch is out of scope here; this skill is the practical, tool-based path.

---

## Table of contents

1. Prerequisites
2. Tesseract OCR (core engine)
   - Windows (UB-Mannheim installer + winget)
   - macOS (Homebrew)
   - Linux (apt)
   - Language packs
   - Tesseract GitHub repository
3. Python packages
4. EasyOCR (stronger fallback)
5. Captioning models (optional)
6. External vision APIs (last resort)
7. Image-to-PDF conversion tools
8. Download links (all-in-one)
9. Verifying the installation
10. Troubleshooting
11. Tesseract page segmentation modes

---

## 1. Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **pip** (latest)
- Network access for the first install (models download on first run)
- ~500 MB free disk for base OCR; ~2 GB if you add captioning models

Check:

```bash
python --version
pip --version
```

---

## 2. Tesseract OCR (core engine)

Tesseract is the open-source OCR engine that does the actual text recognition. Project home and source: **https://github.com/tesseract-ocr/tesseract**

Documentation / downloads portal: **https://tesseractocr.org/**

### 2.1 Windows — UB-Mannheim installer (recommended)

The official Windows builds are maintained by UB Mannheim.

- Download page: https://github.com/UB-Mannheim/tesseract/wiki
- Direct installer (latest): search "tesseract-ocr-w64-setup" on the wiki page above.

Or install via winget (no manual download):

```powershell
winget install UB-Mannheim.TesseractOCR
```

After install, **add Tesseract to your PATH** (the installer usually offers this; if not, add `C:\Program Files\Tesseract-OCR` to PATH manually). Then verify:

```powershell
tesseract --version
```

### 2.2 macOS — Homebrew (recommended)

```bash
brew install tesseract
```

Verify:

```bash
tesseract --version
```

### 2.3 Linux — apt (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y tesseract-ocr
```

For other distros use your package manager (`dnf`, `pacman`, `zypper`) or build from source from the GitHub repo above.

### 2.4 Language packs

Tesseract ships with English by default. Add more languages with Tesseract language codes (combine with `+`):

```bash
# Debian/Ubuntu
sudo apt install -y tesseract-ocr-urd tesseract-ocr-ara tesseract-ocr-hin tesseract-ocr-chi-sim

# macOS (via brew) — languages are usually bundled; check:
brew info tesseract
```

Use in the script:

```bash
python skills/image-sight/scripts/inspect_image.py page.png --mode text --lang eng+urd
```

Common codes: `eng`, `urd`, `ara`, `hin`, `chi_sim`, `chi_tra`, `fra`, `deu`, `spa`, `rus`, `jpn`, `kor`.

### 2.5 Tesseract GitHub repository

- Source code & releases: https://github.com/tesseract-ocr/tesseract
- Wiki (installers, FAQs): https://github.com/tesseract-ocr/tesseract/wiki
- Trained data (language models): https://github.com/tesseract-ocr/tessdata
- Best-quality trained data: https://github.com/tesseract-ocr/tessdata_best

---

## 3. Python packages (minimum)

Covers most documents and screenshots:

```bash
pip install pillow pytesseract --break-system-packages
```

On systems without `--break-system-packages` (older pip), omit that flag or use a virtualenv:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install pillow pytesseract
```

---

## 4. EasyOCR (stronger fallback)

Heavier (downloads models on first run). Better on stylized fonts, photos of signs, and many scripts including Nastaliq Urdu.

```bash
pip install easyocr --break-system-packages
```

First run downloads models (~100 MB+). Warn the user if time matters. EasyOCR is somewhat better than Tesseract on handwriting, but neither is reliable on cursive.

---

## 5. Captioning models (optional)

Gives a one-sentence scene description. Useful for photos, weak for detail.

```bash
pip install transformers torch --break-system-packages
python skills/image-sight/scripts/inspect_image.py photo.jpg --mode describe
```

Notes:

- First run downloads the BLIP model (hundreds of MB). Warn the user if time matters.
- Captions are generic ("a man sitting at a desk with a laptop"). Never present them as complete descriptions.
- For object lists, an object-detection model (e.g. DETR via `transformers`) can be added the same way, but only when the user needs counts or locations.

---

## 6. External vision APIs (last resort)

If local tools cannot answer the question and the user has a vision-capable model or API available, route the image there and explain why (e.g. "this is a photograph where layout and visual detail matter, which OCR cannot capture").

Only call an external service if the user has configured it and consents to the image leaving their machine, since images may hold sensitive data.

Common options: OpenAI GPT-4o vision, Anthropic Claude (vision), Google Gemini, local Ollama with a vision model (e.g. `llava`, `moondream`).

---

## 7. Image-to-PDF conversion tools

Sometimes you need to convert an image to a PDF (e.g. to feed a PDF-based pipeline, or to use Tesseract's PDF output mode). Tools:

### 7.1 img2pdf (recommended, lossless)

```bash
pip install img2pdf
img2pdf input.png -o output.pdf
# multiple images:
img2pdf *.png -o combined.pdf
```

### 7.2 Tesseract (OCR'd searchable PDF)

Tesseract can produce a searchable PDF with an invisible text layer:

```bash
tesseract input.png output pdf
# produces output.pdf
```

With language:

```bash
tesseract input.png output -l eng+urd pdf
```

### 7.3 Pillow (Python, simple)

```python
from PIL import Image
img = Image.open("input.png").convert("RGB")
img.save("output.pdf")
```

### 7.4 ImageMagick (convert)

```bash
# macOS/Linux
convert input.png output.pdf
# or
magick input.png output.pdf
```

Install: https://imagemagick.org/script/download.php

---

## 8. Download links (all-in-one)

| Tool / Resource | Link |
|-----------------|------|
| Tesseract OCR (project home) | https://tesseractocr.org/ |
| Tesseract source & releases | https://github.com/tesseract-ocr/tesseract |
| Tesseract wiki (installers) | https://github.com/tesseract-ocr/tesseract/wiki |
| UB-Mannheim Windows installer | https://github.com/UB-Mannheim/tesseract/wiki |
| Trained language data (tessdata) | https://github.com/tesseract-ocr/tessdata |
| Best-quality trained data | https://github.com/tesseract-ocr/tessdata_best |
| Pillow (PyPI) | https://pypi.org/project/Pillow/ |
| pytesseract (PyPI) | https://pypi.org/project/pytesseract/ |
| EasyOCR (PyPI) | https://pypi.org/project/easyocr/ |
| transformers (PyPI) | https://pypi.org/project/transformers/ |
| img2pdf (PyPI) | https://pypi.org/project/img2pdf/ |
| ImageMagick | https://imagemagick.org/script/download.php |
| Homebrew (macOS) | https://brew.sh/ |
| Python downloads | https://www.python.org/downloads/ |

---

## 9. Verifying the installation

```bash
# Tesseract binary
tesseract --version

# Python packages
python -c "import PIL, pytesseract; print('ok')"

# End-to-end
python skills/image-sight/scripts/inspect_image.py sample.png --mode auto
```

If `inspect_image.py` reports a tool as unavailable, it will name it and suggest the fix. Do not pretend the step succeeded.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Empty output | No text, or very low contrast | Try `--mode text`; check `colors.tone`; try inverted variant (script does this) |
| Random symbols | Wrong language, or non-text image | Set `--lang`; confirm image actually contains text |
| Missing small text | Resolution too low | Script upscales 2x; ask for a higher-resolution original if still missing |
| Columns merged into one stream | Wrong layout mode | Try `--psm 1` or `--psm 4`; use `text_reading_order` |
| Table cells misaligned | Layout lost in plain text | Rebuild rows from `boxes` y-coordinates; see receipts playbook |
| Digits misread (0/O, 1/l, 5/S) | Font or noise | Cross-check arithmetic; flag suspicious tokens |
| Skewed or rotated page | Photo taken at an angle | Rotate with Pillow using EXIF orientation or try 90/180/270 and keep best |
| Handwriting garbled | Tesseract weak on handwriting | Say so plainly; try `easyocr`; offer partial transcript marked uncertain |
| Dark background, light text | Inverted polarity | Script tries inversion; confirm with `mean_brightness` |
| `tesseract: command not found` | Not on PATH | Add install dir to PATH (Windows: `C:\Program Files\Tesseract-OCR`) |
| ModuleNotFoundError | Package not installed | `pip install <package>` |

Rotation retry snippet:

```python
from PIL import Image
import pytesseract
img = Image.open("scan.jpg")
best = max(((a, len(pytesseract.image_to_string(img.rotate(a, expand=True)).split())) for a in (0, 90, 180, 270)),
           key=lambda t: t[1])
print("best rotation:", best)
```

---

## 11. Tesseract page segmentation modes (`--psm`)

| PSM | Meaning | Use for |
|-----|---------|---------|
| 3 | Fully automatic (default) | Most pages |
| 4 | Single column of variable-size text | Receipts, narrow columns |
| 6 | Single uniform block | Clean paragraph or code screenshot |
| 7 | Single text line | Captions, labels, cropped lines |
| 8 | Single word | Cropped words |
| 11 | Sparse text, no order | Charts, posters, scattered labels |
| 12 | Sparse text with orientation detection | Mixed scattered text, rotated |

---

## Notes on small / text-only models

- A 1B / 2B / 7B / 40B parameter text-only model has **no vision**. Do not expect it to "just see" an image.
- You do **not** need to fine-tune or train a custom model. The reliable path is: give the model tools (this skill's `inspect_image.py` + Tesseract) that convert pixels to text, then let the model reason over the text.
- If you truly need native visual understanding (faces, scenes, fine detail), use a vision-capable model (GPT-4o, Claude, Gemini, or a local VLM like LLaVA/moondream) — see section 6.
- Never fabricate image content. If the tools fail, report the failure and offer a path forward.
