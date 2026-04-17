"""Build omr_a4.pdf — A4 pages packed with as many licks as comfortably fit.

Layout oemer expects: a normal sheet-music page with several staves, generous
whitespace between them, staff lines crisp at ~300 DPI. No titles, no labels.

Dynamic packer: add licks until the next one won't fit in remaining vertical
space, then start a new page. Double-staff licks naturally get more room.
"""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
PNG_DIR = HERE / "pngs"
OUT = HERE / "omr_a4.pdf"

# A4 at 300 DPI
PAGE_W, PAGE_H = 2480, 3508
MARGIN = 180
GAP = 80        # generous vertical whitespace between licks
IMG_W = 2120    # image width — fits inside margins

def load_white(p):
    im = Image.open(p)
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        im = bg
    else:
        im = im.convert("RGB")
    # Uniform width (preserves aspect)
    h = int(round(im.height * IMG_W / im.width))
    return im.resize((IMG_W, h), Image.LANCZOS)

def pack_pages(images):
    """Greedy vertical packing — new page when next image doesn't fit."""
    usable = PAGE_H - 2 * MARGIN
    pages = []
    cur = []; cur_h = 0
    for im in images:
        need = im.height + (GAP if cur else 0)
        if cur_h + need > usable:
            pages.append(cur)
            cur = [im]; cur_h = im.height
        else:
            cur.append(im); cur_h += need
    if cur:
        pages.append(cur)
    return pages

def render_page(images):
    page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    total = sum(im.height for im in images) + (len(images) - 1) * GAP
    y = MARGIN + (PAGE_H - 2 * MARGIN - total) // 2   # center vertically
    x = (PAGE_W - IMG_W) // 2
    for i, im in enumerate(images):
        page.paste(im, (x, y))
        y += im.height + GAP
    return page

def main():
    import json
    sources = sorted(PNG_DIR.glob("[0-9][0-9]licks.png"))
    assert len(sources) == 100, f"expected 100, got {len(sources)}"
    images = [load_white(p) for p in sources]
    print(f"[scan] single-ish (h<400): {sum(1 for im in images if im.height < 500)} "
          f"  double-ish: {sum(1 for im in images if im.height >= 500)}")
    # Re-pack with lick indices tracked
    usable = PAGE_H - 2 * MARGIN
    pages_lists = []
    mapping = []   # per page: list of lick indices (0-99)
    cur = []; cur_h = 0; cur_idx = []
    for idx, im in enumerate(images):
        need = im.height + (GAP if cur else 0)
        if cur_h + need > usable:
            pages_lists.append(cur); mapping.append(cur_idx)
            cur = [im]; cur_h = im.height; cur_idx = [idx]
        else:
            cur.append(im); cur_h += need; cur_idx.append(idx)
    if cur:
        pages_lists.append(cur); mapping.append(cur_idx)
    print(f"[pack] {len(pages_lists)} pages, counts per page: "
          f"{[len(p) for p in pages_lists]}")
    (HERE / "omr_a4_mapping.json").write_text(json.dumps(mapping, indent=2))
    rendered = [render_page(p) for p in pages_lists]
    rendered[0].save(OUT, save_all=True, append_images=rendered[1:],
                     format="PDF", resolution=300.0)
    print(f"[done] wrote {OUT} ({len(rendered)} pages), mapping in omr_a4_mapping.json")

if __name__ == "__main__":
    main()
