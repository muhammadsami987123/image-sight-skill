#!/usr/bin/env python3
"""
inspect_image.py - Turn an image into structured, text-only evidence.

Designed for language models that cannot see images. Runs a fallback chain of
tools and prints a JSON report. Optional dependencies are never required: the
report lists what was unavailable so the caller can say so honestly.

Usage:
    python inspect_image.py IMAGE [--mode auto|text|describe|full]
                                  [--lang eng] [--psm 3] [--out report.json]
"""

import argparse
import json
import os
import shutil
import sys
from collections import Counter

try:
    from PIL import Image, ImageOps, ImageFilter, ExifTags
except ImportError:
    print(json.dumps({"error": "Pillow is required: pip install pillow"}))
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Metadata
# --------------------------------------------------------------------------- #

def get_metadata(path, img):
    meta = {
        "file_name": os.path.basename(path),
        "file_size_kb": round(os.path.getsize(path) / 1024, 1),
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
        "aspect_ratio": round(img.width / img.height, 3) if img.height else None,
        "megapixels": round(img.width * img.height / 1e6, 2),
        "animated": bool(getattr(img, "is_animated", False)),
        "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info,
    }
    exif = {}
    try:
        raw = img.getexif()
        for tag_id, value in raw.items():
            tag = ExifTags.TAGS.get(tag_id, str(tag_id))
            if tag in ("DateTime", "DateTimeOriginal", "Make", "Model", "Software",
                       "Orientation", "ImageDescription", "Artist", "Copyright"):
                exif[tag] = str(value)[:200]
        gps = raw.get_ifd(0x8825) if hasattr(raw, "get_ifd") else None
        if gps:
            exif["has_gps_data"] = True  # presence only; coordinates are not echoed
    except Exception:
        pass
    if exif:
        meta["exif"] = exif
    return meta


# --------------------------------------------------------------------------- #
# Color / brightness analysis
# --------------------------------------------------------------------------- #

NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "gray": (128, 128, 128),
    "red": (220, 40, 40), "orange": (240, 140, 30), "yellow": (240, 220, 40),
    "green": (50, 160, 60), "teal": (20, 150, 150), "blue": (40, 90, 200),
    "purple": (130, 60, 170), "pink": (240, 130, 180), "brown": (130, 80, 40),
}


def nearest_color_name(rgb):
    r, g, b = rgb
    spread = max(rgb) - min(rgb)
    if spread < 28:  # low saturation: neutral shades, name by lightness
        lum = (r + g + b) / 3
        return "black" if lum < 60 else "white" if lum > 200 else "gray"
    return min(NAMED_COLORS, key=lambda n: sum((a - c) ** 2 for a, c in zip(rgb, NAMED_COLORS[n])))


def pixels_of(image):
    """Version-safe pixel access (Pillow 14 removes getdata)."""
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def analyze_colors(img, k=5):
    small = img.convert("RGB").resize((96, 96))
    quant = small.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    palette = quant.getpalette()[: k * 3]
    counts = Counter(pixels_of(quant))
    total = sum(counts.values())
    result = []
    for idx, cnt in counts.most_common(k):
        rgb = tuple(palette[idx * 3: idx * 3 + 3])
        result.append({
            "hex": "#%02x%02x%02x" % rgb,
            "approx_name": nearest_color_name(rgb),
            "share_percent": round(100 * cnt / total, 1),
        })
    gray = small.convert("L")
    pixels = pixels_of(gray)
    mean = sum(pixels) / len(pixels)
    return {
        "dominant_colors": result,
        "mean_brightness_0_255": round(mean, 1),
        "tone": "dark" if mean < 85 else "light" if mean > 170 else "mid",
    }


# --------------------------------------------------------------------------- #
# OCR
# --------------------------------------------------------------------------- #

def preprocess_variants(img):
    """Yield (name, image) variants that often rescue poor OCR."""
    base = ImageOps.exif_transpose(img).convert("RGB")
    gray = ImageOps.grayscale(base)
    yield "original", base
    yield "gray_autocontrast", ImageOps.autocontrast(gray)
    scale = 2 if max(gray.size) < 1800 else 1
    if scale > 1:
        up = gray.resize((gray.width * scale, gray.height * scale), Image.LANCZOS)
        yield "upscaled_2x", ImageOps.autocontrast(up)
    thr = ImageOps.autocontrast(gray).point(lambda p: 255 if p > 150 else 0)
    yield "binarized", thr
    yield "inverted", ImageOps.invert(ImageOps.autocontrast(gray))
    yield "sharpened", ImageOps.autocontrast(gray).filter(ImageFilter.SHARPEN)


def run_tesseract(img, lang, psm):
    try:
        import pytesseract
    except ImportError:
        return None, "pytesseract not installed (pip install pytesseract)"
    if not shutil.which("tesseract"):
        return None, "tesseract binary not found (apt install tesseract-ocr)"
    config = f"--psm {psm}"
    try:
        data = pytesseract.image_to_data(img, lang=lang, config=config,
                                         output_type=pytesseract.Output.DICT)
    except Exception as exc:
        return None, f"tesseract failed: {exc}"
    words, confs, boxes = [], [], []
    for i, txt in enumerate(data["text"]):
        txt = txt.strip()
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1
        if txt and conf >= 0:
            words.append(txt)
            confs.append(conf)
            boxes.append({
                "text": txt, "conf": round(conf, 1),
                "x": data["left"][i], "y": data["top"][i],
                "w": data["width"][i], "h": data["height"][i],
                "line": (data["block_num"][i], data["par_num"][i], data["line_num"][i]),
            })
    try:
        text = pytesseract.image_to_string(img, lang=lang, config=config).strip()
    except Exception:
        text = " ".join(words)
    return {
        "text": text,
        "word_count": len(words),
        "mean_confidence": round(sum(confs) / len(confs), 1) if confs else 0.0,
        "boxes": boxes,
    }, None


def run_easyocr(img, lang):
    try:
        import easyocr
        import numpy as np
    except ImportError:
        return None, "easyocr not installed (pip install easyocr)"
    langs = [{"eng": "en", "urd": "ur", "ara": "ar", "hin": "hi"}.get(c, c)
             for c in lang.split("+")]
    try:
        reader = easyocr.Reader(langs, gpu=False, verbose=False)
        results = reader.readtext(np.array(img.convert("RGB")))
    except Exception as exc:
        return None, f"easyocr failed: {exc}"
    lines = [r[1] for r in results]
    confs = [r[2] * 100 for r in results]
    return {
        "text": "\n".join(lines),
        "word_count": sum(len(l.split()) for l in lines),
        "mean_confidence": round(sum(confs) / len(confs), 1) if confs else 0.0,
        "boxes": [],
    }, None


def best_ocr(img, lang, psm, try_variants=True):
    """Try tesseract across preprocessing variants, then easyocr as fallback."""
    notes, best, best_variant = [], None, None
    variants = preprocess_variants(img) if try_variants else [("original", img.convert("RGB"))]
    for name, variant in variants:
        res, err = run_tesseract(variant, lang, psm)
        if err:
            notes.append(err)
            break
        score = res["mean_confidence"] * min(res["word_count"], 50) ** 0.5
        if best is None or score > best[0]:
            best, best_variant = (score, res), name
        if res["mean_confidence"] > 90 and res["word_count"] > 5:
            break  # good enough; skip remaining variants
    if best and best[1]["word_count"] > 0 and best[1]["mean_confidence"] >= 50:
        result = best[1]
        result["engine"] = "tesseract"
        result["preprocessing"] = best_variant
        return result, notes
    # Fallback to easyocr when tesseract is missing or weak
    alt, err = run_easyocr(img, lang)
    if err:
        notes.append(err)
    if alt and alt["word_count"] > 0:
        alt["engine"] = "easyocr"
        return alt, notes
    if best:
        result = best[1]
        result["engine"] = "tesseract (low confidence)"
        result["preprocessing"] = best_variant
        return result, notes
    return None, notes


def layout_hints(ocr, img):
    """Cheap, evidence-based layout cues derived from OCR boxes."""
    if not ocr or not ocr.get("boxes"):
        return {}
    boxes = ocr["boxes"]
    img_area = img.width * img.height
    text_area = sum(b["w"] * b["h"] for b in boxes)
    lines = {}
    for b in boxes:
        lines.setdefault(b["line"], []).append(b)
    xs = [min(b["x"] for b in v) for v in lines.values()]
    numeric = sum(1 for b in boxes if any(c.isdigit() for c in b["text"]))
    return {
        "text_coverage_percent": round(100 * text_area / img_area, 1),
        "line_count": len(lines),
        "numeric_token_ratio": round(numeric / len(boxes), 2),
        "distinct_left_margins": len({round(x / max(img.width * 0.03, 1)) for x in xs}),
    }


def reading_order_text(ocr):
    """Rebuild text line by line (top-to-bottom, left-to-right) from boxes."""
    if not ocr or not ocr.get("boxes"):
        return None
    lines = {}
    for b in ocr["boxes"]:
        lines.setdefault(b["line"], []).append(b)
    ordered = sorted(lines.values(), key=lambda v: (min(b["y"] for b in v), min(b["x"] for b in v)))
    return "\n".join(" ".join(b["text"] for b in sorted(v, key=lambda b: b["x"])) for v in ordered)


# --------------------------------------------------------------------------- #
# Captioning (optional, heavier)
# --------------------------------------------------------------------------- #

def run_caption(img):
    try:
        from transformers import pipeline
    except ImportError:
        return None, "transformers not installed (pip install transformers torch)"
    try:
        captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
        out = captioner(img.convert("RGB"))
        return out[0]["generated_text"], None
    except Exception as exc:
        return None, f"captioning unavailable: {exc}"


# --------------------------------------------------------------------------- #
# Type guess (heuristic, always reported as a guess)
# --------------------------------------------------------------------------- #

def guess_type(meta, ocr, hints):
    if not ocr or ocr["word_count"] < 3:
        return {"guess": "photo or graphic with little text", "confidence": "low"}
    cov = hints.get("text_coverage_percent", 0)
    num = hints.get("numeric_token_ratio", 0)
    ar = meta.get("aspect_ratio") or 1
    text = ocr["text"].lower()
    if any(k in text for k in ("total", "subtotal", "invoice", "receipt", "amount due", "tax")) and num > 0.2:
        return {"guess": "receipt or invoice", "confidence": "medium"}
    if ar < 0.5 and cov > 5:
        return {"guess": "long screenshot or receipt strip", "confidence": "low"}
    if cov > 12:
        return {"guess": "document, article, or text-heavy screenshot", "confidence": "medium"}
    if num > 0.5 and hints.get("line_count", 0) < 25:
        return {"guess": "chart, table, or dashboard", "confidence": "low"}
    return {"guess": "mixed content (screenshot, slide, or poster)", "confidence": "low"}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--mode", choices=["auto", "text", "describe", "full"], default="auto")
    ap.add_argument("--lang", default="eng", help="Tesseract language codes, e.g. eng+urd")
    ap.add_argument("--psm", type=int, default=3, help="Tesseract page segmentation mode")
    ap.add_argument("--out", help="Also write the JSON report to this path")
    args = ap.parse_args()

    if not os.path.isfile(args.image):
        print(json.dumps({"error": f"File not found: {args.image}"}))
        sys.exit(1)
    try:
        img = Image.open(args.image)
        img.load()
    except Exception as exc:
        print(json.dumps({"error": f"Cannot open as image: {exc}"}))
        sys.exit(1)

    report = {"mode": args.mode, "unavailable_or_failed": []}
    report["metadata"] = get_metadata(args.image, img)

    if args.mode != "text":
        report["colors"] = analyze_colors(img)

    ocr = None
    if args.mode in ("auto", "text", "full", "describe"):
        ocr, notes = best_ocr(img, args.lang, args.psm, try_variants=args.mode != "describe")
        report["unavailable_or_failed"].extend(notes)
        if ocr:
            ordered = reading_order_text(ocr)
            report["ocr"] = {
                "engine": ocr.get("engine"),
                "preprocessing": ocr.get("preprocessing"),
                "word_count": ocr["word_count"],
                "mean_confidence_0_100": ocr["mean_confidence"],
                "text": ocr["text"],
                "text_reading_order": ordered if ordered and ordered != ocr["text"] else None,
                "low_confidence_words": [b["text"] for b in ocr["boxes"] if b["conf"] < 60][:40],
            }
            if args.mode != "text":
                report["layout_hints"] = layout_hints(ocr, img)
        else:
            report["ocr"] = {"text": "", "word_count": 0,
                             "note": "No text extracted. Image may contain no text, or OCR tools are missing."}

    if args.mode in ("describe", "full"):
        caption, err = run_caption(img)
        if caption:
            report["caption"] = {"text": caption, "model": "blip-image-captioning-base",
                                 "caveat": "Short, generic caption; misses fine detail."}
        elif err:
            report["unavailable_or_failed"].append(err)

    if args.mode in ("auto", "full"):
        report["type_guess"] = guess_type(report["metadata"], ocr, report.get("layout_hints", {}))

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
