# scripts/try_vlm.py

import sys
from pathlib import Path

from forms.registry import get_form
from ingestion.ingestion import extract_form
from ingestion.loading import load_pages

spec = get_form(sys.argv[1])
engine = sys.argv[2]
path = Path(sys.argv[3])
page_number = int(sys.argv[4]) if len(sys.argv) > 4 else 1

pages = load_pages(path.read_bytes(), path.name)
image = pages[page_number - 1]
print(extract_form(image, spec, engine).model_dump_json(indent=2))
