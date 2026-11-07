# scripts/draw_layout.py

import sys
from pathlib import Path

from PIL import ImageDraw

from forms.layout import Box, TableLayout
from forms.registry import get_form
from ingestion.loading import load_pages

spec = get_form(sys.argv[1])
path = Path(sys.argv[2])
page_number = int(sys.argv[3]) if len(sys.argv) > 3 else 1

image = load_pages(path.read_bytes(), path.name)[page_number - 1].convert("RGB")
width, height = image.size
draw = ImageDraw.Draw(image)

boxes: list[Box]
if isinstance(spec.layout, TableLayout):
    boxes = [
        spec.layout.cell(row, column)
        for row in range(spec.layout.n_rows)
        for column in spec.layout.columns
    ]
else:
    boxes = list(spec.layout.values())

for x0, y0, x1, y1 in boxes:
    draw.rectangle(
        (x0 * width, y0 * height, x1 * width, y1 * height), outline="red", width=3
    )

out = Path("data/samples") / f"layout_{spec.key}_p{page_number}.png"
image.save(out)
print(f"Saved {out}")
