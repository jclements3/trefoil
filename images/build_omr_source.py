"""Build OMR source PDFs — tabloid (11x17"), 10 licks/page, no labels.

Splits into 2 files of 50 licks each so each stays within the 5-page
upload limit of the online PDF→MusicXML service.
Per-strip height is generous so OMR captures every lick cleanly
(the 20/page density test dropped ~60% of licks).
"""
import sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
PNG_DIR = HERE / "pngs"

# Tabloid at 300 DPI
PAGE_W, PAGE_H = 3300, 5100
MARGIN_TOP = 100
MARGIN_BOT = 100
GAP = 30
PER_PAGE = 10

def load_white(p):
    im = Image.open(p)
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        return bg
    return im.convert("RGB")

def build_pdf(images, out_path):
    usable = PAGE_H - MARGIN_TOP - MARGIN_BOT
    pages = []
    for start in range(0, len(images), PER_PAGE):
        page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
        y = MARGIN_TOP
        batch = images[start : start + PER_PAGE]
        # Simple per-page overflow check — should never trigger at 10/page
        page_content = sum(im.height for im in batch) + (len(batch) - 1) * GAP
        if page_content > usable:
            raise RuntimeError(f"page {len(pages)} overflows: "
                               f"{page_content}px > {usable}px usable")
        for im in batch:
            x = (PAGE_W - im.width) // 2
            page.paste(im, (x, y))
            y += im.height + GAP
        pages.append(page)
    pages[0].save(out_path, save_all=True, append_images=pages[1:],
                  format="PDF", resolution=300.0)
    print(f"[done] wrote {out_path} ({len(pages)} pages, "
          f"{len(images)} licks)")

def main():
    sources = sorted(PNG_DIR.glob("[0-9][0-9]licks.png"))
    assert len(sources) == 100, f"expected 100, got {len(sources)}"
    images = [load_white(p) for p in sources]
    build_pdf(images[:50],  HERE / "omr_source_A.pdf")
    build_pdf(images[50:], HERE / "omr_source_B.pdf")

if __name__ == "__main__":
    main()
