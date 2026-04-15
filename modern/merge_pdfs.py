"""Merge PDF files into one.

Uses poppler's ``pdfunite`` when available, otherwise falls back to
``PyPDF2`` / ``pypdf``. Raises ``RuntimeError`` if neither is usable.

CLI:
    python3.10 modern/merge_pdfs.py OUTPUT INPUT1 INPUT2 [INPUT3 ...]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _merge_with_pdfunite(output_path: str, input_paths: list[str]) -> None:
    cmd = ["pdfunite", *input_paths, output_path]
    subprocess.run(cmd, check=True)


def _merge_with_pypdf(output_path: str, input_paths: list[str]) -> None:
    # Try pypdf first (newer), then PyPDF2.
    try:
        from pypdf import PdfWriter  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfWriter  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Neither pdfunite, pypdf, nor PyPDF2 available for PDF merge."
            ) from exc

    writer = PdfWriter()
    for path in input_paths:
        writer.append(path)
    with open(output_path, "wb") as fh:
        writer.write(fh)
    writer.close()


def merge(output_path: str, *input_paths: str) -> None:
    """Merge ``input_paths`` into ``output_path``.

    Tries ``pdfunite`` first (fast, preserves everything). If absent,
    falls back to ``pypdf``/``PyPDF2``. Raises ``RuntimeError`` if no
    backend is available or the underlying tool fails.
    """
    if not input_paths:
        raise ValueError("merge() requires at least one input PDF")
    for p in input_paths:
        if not os.path.isfile(p):
            raise FileNotFoundError(p)

    out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(out_dir, exist_ok=True)

    if shutil.which("pdfunite"):
        try:
            _merge_with_pdfunite(output_path, list(input_paths))
            return
        except subprocess.CalledProcessError as exc:
            # Fall through to pypdf backend.
            last_err: Exception = exc
    else:
        last_err = RuntimeError("pdfunite not found on PATH")

    try:
        _merge_with_pypdf(output_path, list(input_paths))
    except Exception as exc:
        raise RuntimeError(
            f"PDF merge failed; pdfunite error: {last_err!r}; pypdf error: {exc!r}"
        ) from exc


def _main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: python3.10 modern/merge_pdfs.py OUTPUT INPUT1 INPUT2 [INPUT3 ...]",
            file=sys.stderr,
        )
        return 2
    output_path = argv[1]
    input_paths = argv[2:]
    merge(output_path, *input_paths)
    print(f"wrote {output_path} ({len(input_paths)} inputs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
