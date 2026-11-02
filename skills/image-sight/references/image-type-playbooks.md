# Image Type Playbooks

Read only the section that matches the image type you identified. Every playbook follows the same rule: **report what the tools extracted, label inferences as inferences.**

## Contents
1. Scanned documents and articles
2. Receipts and invoices
3. Screenshots and UI
4. Charts and graphs
5. Diagrams and flowcharts
6. Photos and scenes
7. Handwriting
8. Multilingual and right-to-left text
9. IDs, cards, and sensitive documents
10. Memes and text-over-image graphics

---

## 1. Scanned documents and articles

**Goal:** accurate text in correct reading order.

- Use `--mode text --psm 3` first; try `--psm 1` for multi-column layouts.
- Use `text_reading_order` when the plain `text` field interleaves columns.
- Preserve paragraph breaks; rebuild headings from line height (taller boxes are usually headings).
- Report page-level issues: skew, cut-off margins, faded regions.
- For long documents, summarize only after extraction is confirmed complete.

## 2. Receipts and invoices

**Goal:** structured fields with arithmetic that checks out.

- Use `--psm 4` (single column) or `--psm 6`.
- Extract: merchant, date, line items (name, quantity, unit price, line total), subtotal, tax, total, payment method.
- Rebuild rows by grouping boxes with similar `y` values; the rightmost numeric token on a row is usually the line total.
- **Verify:** sum of line totals plus tax should equal the total. If not, name the most likely misread token instead of silently correcting it.
- Flag ambiguous currency symbols and date formats (day-month versus month-day).

Output as a table when the user wants data, as a sentence when they only want the total.

## 3. Screenshots and UI

**Goal:** what the screen says and what actions are available.

- Use `--psm 11` (sparse) when the screen has scattered labels; `--psm 6` for code or terminal screenshots.
- Group text by vertical position: top = title or nav bar, middle = content, bottom = actions or status.
- Error messages, stack traces, and URLs are high-value: quote them verbatim.
- For code screenshots, warn that OCR commonly confuses `l`, `1`, `I`, `0`, `O`, quotes, and indentation. Never present OCR'd code as guaranteed-correct; suggest the user paste the text if exactness matters.
- Cannot determine from OCR: icons without labels, colors that signal state (red error, green success). Use the `colors` data as a weak hint and say so.

## 4. Charts and graphs

**Goal:** report what is actually readable; do not invent data points.

OCR recovers titles, axis labels, tick values, legends, and annotations. It does **not** recover bar heights, line positions, or slice sizes.

- Extract title, axis labels, units, legend entries, and any data labels printed on the chart.
- If values are printed on the chart, report them exactly.
- If values are not printed, say: "The chart shows [title] with [axes]. Exact values are not readable from text alone." Offer estimates only if you can compute them, for example by measuring pixel positions with Pillow against axis ticks, and label them clearly as estimates with approximate error.
- Optional pixel measurement: locate colored bar extents by scanning columns of the dominant palette colors, then map pixel height to axis values using two known tick positions.

## 5. Diagrams and flowcharts

**Goal:** node labels and likely relationships, with honest uncertainty about edges.

- Extract all text labels; they are the nodes.
- Connections (arrows) are not recoverable from OCR. Present the labels, then offer a *proposed* flow based on spatial layout (top-to-bottom, left-to-right) clearly marked as a guess.
- Ask the user to confirm the structure when it matters.

## 6. Photos and scenes

**Goal:** a modest, truthful description.

- Use `--mode describe`. Combine caption, dominant colors, brightness, metadata (camera, date, orientation, GPS presence), and any OCR text (signs, labels, shirts).
- Present as: "Caption model output: ...; text found in image: ...; dominant colors: ...".
- Do not claim to see people's expressions, ages, identities, or small objects unless a tool reported them.
- Do not identify people from faces under any circumstances.
- If the user needs detailed visual understanding of a photo, say that a vision-capable model is the right tool, and offer what the text-based pipeline did produce.

## 7. Handwriting

- Tesseract is weak on handwriting; `easyocr` is somewhat better. Neither is reliable on cursive.
- Provide a best-effort transcript with uncertain words in brackets, for example `meeting at [3pm?]`.
- Say plainly that handwriting recognition is approximate. For anything consequential (medical notes, legal text, amounts), ask the user to confirm the transcript.

## 8. Multilingual and right-to-left text

- Set `--lang` with the right pack (`eng+urd`, `ara`, `hin`, `chi_sim`, and so on). Mixing languages in one pass lowers accuracy slightly; if results are poor, run each language separately and merge.
- Right-to-left scripts (Urdu, Arabic) may come out with reversed word order in some engines. Check a known phrase and reverse line order if needed.
- Nastaliq Urdu is hard for Tesseract; prefer `easyocr` and flag moderate confidence.
- Answer in the user's language, quoting the extracted text in its original script.

## 9. IDs, cards, and sensitive documents

- Extract only the fields the user's task requires.
- Do not repeat full ID numbers, card numbers, or account numbers in the response; mask all but the last four characters unless the user explicitly needs the full value for their own use.
- Do not use extracted personal data for anything beyond the stated task.
- Do not verify authenticity ("this ID is real or fake"); text extraction cannot establish that.

## 10. Memes and text-over-image graphics

- OCR gives the caption text; it cannot give the image behind it.
- Report the text, then say what the visual context would have added: "The meme's joke likely depends on the image, which I cannot see; the text reads: ...".
- Do not guess the template, the people, or the punchline from text alone unless the text itself makes it clear.
