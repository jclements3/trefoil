"""Assemble pngs/{00..99}licks.png into a single PDF, labeled, for side-by-side
checking against pianolicks.pdf and harplicks.pdf transcriptions.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

IMG_DIR = Path(__file__).parent
PNG_DIR = IMG_DIR / "pngs"
OUT = IMG_DIR / "sourcelicks.pdf"

PAGE_W, PAGE_H = 1700, 2200         # letter-ish @ 200dpi
MARGIN = 40
LABEL_H = 40
GAP = 20
PER_PAGE = 6                        # licks per page

def find_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def main():
    label_font = find_font(32)
    pages = []
    licks = sorted(PNG_DIR.glob("[0-9][0-9]licks.png"))
    if not licks:
        raise SystemExit("no licks found")
    # Compute max strip width to fit page
    strip_w = PAGE_W - 2 * MARGIN
    slot_h = (PAGE_H - 2 * MARGIN - (PER_PAGE - 1) * GAP) // PER_PAGE
    img_h = slot_h - LABEL_H

    for page_start in range(0, len(licks), PER_PAGE):
        page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
        draw = ImageDraw.Draw(page)
        y = MARGIN
        for lick_path in licks[page_start : page_start + PER_PAGE]:
            # Label
            label = f"Lick {lick_path.stem[:2]}"
            draw.text((MARGIN, y), label, fill="black", font=label_font)
            y += LABEL_H
            # Image, scaled to fit width
            im = Image.open(lick_path)
            if im.mode == "RGBA":
                bg = Image.new("RGB", im.size, "white")
                bg.paste(im, mask=im.split()[3])
                im = bg
            else:
                im = im.convert("RGB")
            scale = min(strip_w / im.width, img_h / im.height)
            new_w, new_h = int(im.width * scale), int(im.height * scale)
            im = im.resize((new_w, new_h), Image.LANCZOS)
            page.paste(im, (MARGIN, y))
            y += img_h + GAP - LABEL_H + LABEL_H  # reset for slot layout
            y = y if y == MARGIN + LABEL_H + img_h + GAP else y
            # simpler: just advance by slot_h + GAP - LABEL_H (already added label)
            y = y  # (kept simple — advance happens naturally below)
        # Rebuild y deterministically
        page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
        draw = ImageDraw.Draw(page)
        y = MARGIN
        for lick_path in licks[page_start : page_start + PER_PAGE]:
            label = f"Lick {lick_path.stem[:2]}"
            draw.text((MARGIN, y), label, fill="black", font=label_font)
            im = Image.open(lick_path)
            if im.mode == "RGBA":
                bg = Image.new("RGB", im.size, "white")
                bg.paste(im, mask=im.split()[3])
                im = bg
            else:
                im = im.convert("RGB")
            scale = min(strip_w / im.width, img_h / im.height)
            new_w, new_h = int(im.width * scale), int(im.height * scale)
            im = im.resize((new_w, new_h), Image.LANCZOS)
            page.paste(im, (MARGIN, y + LABEL_H))
            y += slot_h + GAP
        pages.append(page)

    pages[0].save(OUT, save_all=True, append_images=pages[1:],
                  format="PDF", resolution=200.0)
    print(f"wrote {OUT}  ({len(pages)} pages)")

if __name__ == "__main__":
    main()
