"""Build review PDF: source PNG + rendered ABC clone for all 100 licks.

Runs abcm2ps on licks.abc (once, batching), converts each EPS to PNG with gs,
crops each to its content bbox, then assembles pages: 2 licks per page with
source on top and ABC render below.
"""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
PNG_DIR = HERE / "pngs"
ABC_SRC = HERE / "licks.abc"
OUT = HERE / "review.pdf"

PAGE_W, PAGE_H = 1700, 2200      # letter-ish @ 200dpi
MARGIN = 60
PER_PAGE = 2                     # two licks per page
GAP_BLOCKS = 80                  # gap between consecutive licks
GAP_PAIR = 20                    # gap between source and ABC for same lick
LABEL_H = 44
HEADER = """%abc-2.1
%%leftmargin 1.0cm
%%rightmargin 1.0cm
%%topspace 0.2cm
%%musicspace 0.4cm
%%staffsep 30pt
%%scale 0.85

"""

def find_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def render_abc(tmp: Path) -> list[Path]:
    """Run abcm2ps on licks.abc with formatting header; return sorted PNGs."""
    abc_file = tmp / "licks.abc"
    abc_file.write_text(HEADER + ABC_SRC.read_text().split("\n\n", 1)[-1])
    # abcm2ps -E -O abc_ -> abc_001.eps .. abc_100.eps
    subprocess.run(
        ["abcm2ps", "-E", "-O", "abc_", str(abc_file)],
        cwd=tmp, check=True, stdout=subprocess.DEVNULL,
    )
    eps_files = sorted(tmp.glob("abc_*.eps"))
    png_files = []
    for eps in eps_files:
        png = eps.with_suffix(".png")
        subprocess.run(
            ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pngalpha",
             "-r200", f"-sOutputFile={png}", str(eps)],
            check=True, stdout=subprocess.DEVNULL,
        )
        png_files.append(png)
    return png_files

def crop_to_content(im: Image.Image, pad: int = 15) -> Image.Image:
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        im = bg
    else:
        im = im.convert("RGB")
    arr = np.asarray(im.convert("L"))
    dark = arr < 200
    ys, xs = np.where(dark)
    if len(xs) == 0:
        return im
    y0 = max(0, ys.min() - pad)
    y1 = min(arr.shape[0], ys.max() + pad + 1)
    x0 = max(0, xs.min() - pad)
    x1 = min(arr.shape[1], xs.max() + pad + 1)
    return im.crop((x0, y0, x1, y1))

def load_source(path: Path) -> Image.Image:
    im = Image.open(path)
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[3])
        im = bg
    else:
        im = im.convert("RGB")
    return im

def scale_to_width(im: Image.Image, target_w: int) -> Image.Image:
    if im.width == target_w:
        return im
    h = int(round(im.height * target_w / im.width))
    return im.resize((target_w, h), Image.LANCZOS)

def main():
    with tempfile.TemporaryDirectory() as tmpname:
        tmp = Path(tmpname)
        print("[render] running abcm2ps + gs ...")
        abc_pngs = render_abc(tmp)
        print(f"[render] got {len(abc_pngs)} ABC renders")

        sources = sorted(PNG_DIR.glob("[0-9][0-9]licks.png"))
        assert len(sources) == 100, f"expected 100 sources, got {len(sources)}"
        n = min(len(sources), len(abc_pngs))
        print(f"[pair] building PDF for {n} licks")

        label_font = find_font(30)
        sub_font = find_font(20)
        content_w = PAGE_W - 2 * MARGIN

        pages = []
        for page_start in range(0, n, PER_PAGE):
            page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
            draw = ImageDraw.Draw(page)
            y = MARGIN
            for idx in range(page_start, min(page_start + PER_PAGE, n)):
                src = scale_to_width(load_source(sources[idx]), content_w)
                abc = scale_to_width(crop_to_content(Image.open(abc_pngs[idx])), content_w)
                # Labels
                draw.text((MARGIN, y), f"Lick {idx:02d}", fill="black", font=label_font)
                y += LABEL_H
                draw.text((MARGIN, y), "Source (video still):", fill="gray", font=sub_font)
                y += 26
                page.paste(src, (MARGIN, y))
                y += src.height + GAP_PAIR
                draw.text((MARGIN, y), "ABC clone (rendered):", fill="gray", font=sub_font)
                y += 26
                page.paste(abc, (MARGIN, y))
                y += abc.height + GAP_BLOCKS
            pages.append(page)

        pages[0].save(OUT, save_all=True, append_images=pages[1:],
                      format="PDF", resolution=200.0)
        print(f"[done] wrote {OUT} ({len(pages)} pages)")

if __name__ == "__main__":
    main()
