from pathlib import Path
import re

import pdfplumber


base = Path(r"C:\Users\aw4wz\Documents\Codex\TLaser\Docs\bases")

for p in sorted(base.glob("*.pdf")):
    print(f"\n==== {p.name} size {p.stat().st_size}")
    try:
        with pdfplumber.open(str(p)) as pdf:
            print(f"pages {len(pdf.pages)}")
            chunks = []
            for page in pdf.pages[:3]:
                chunks.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
            text = re.sub(r"\s+", " ", "\n".join(chunks)).strip()
            print(text[:1600] if text else "[NO TEXT EXTRACTED]")
    except Exception as exc:
        print(f"ERR {type(exc).__name__}: {exc}")
