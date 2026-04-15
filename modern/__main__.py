"""CLI dispatcher for the modern/ hymnal pipeline.

Usage:
    python3.10 -m modern                    # print help
    python3.10 -m modern <subcommand> [args]

Subcommands:
    samples  all  perkey  index  stats  test  find  audit  clean  help
"""

import difflib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys


MODERN_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(MODERN_DIR)
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")


SUBCOMMANDS = [
    ("samples", "Run modern.verify_samples (10-hymn sample PDF)"),
    ("all",     "Run modern.build_all (full 287 hymns PDF)"),
    ("perkey",  "Run modern.build_per_key (8 per-key PDFs)"),
    ("index",   "Build modern/hymn_index.pdf via lilypond"),
    ("stats",   "Run modern.build_stats (stats dashboard)"),
    ("test",    "Run unittest suite (reharm, voicing, abc, integration)"),
    ("find",    "Fuzzy search hymn titles: find <title>"),
    ("audit",   "Run modern.audit_keys and modern.analyze_variety"),
    ("clean",   "Delete generated files in modern/ (use -y to skip prompt)"),
    ("help",    "Print this help"),
]


def print_help() -> int:
    print("Usage: python3.10 -m modern <subcommand> [args]")
    print()
    print("Subcommands:")
    for name, desc in SUBCOMMANDS:
        print("  %-8s  %s" % (name, desc))
    return 0


def run_module(modname: str) -> int:
    """Import modern.<modname> and invoke its main() if present.

    Returns exit code. Handles missing module / missing main() gracefully.
    """
    full = "modern." + modname
    try:
        mod = importlib.import_module(full)
    except ImportError as exc:
        print("[modern] Module '%s' is not yet implemented (%s)."
              % (full, exc))
        return 1
    except Exception as exc:
        print("[modern] Failed to import %s: %s" % (full, exc))
        return 1

    if hasattr(mod, "main") and callable(mod.main):
        try:
            rc = mod.main()
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 1
        except Exception as exc:
            print("[modern] %s.main() raised: %s" % (full, exc))
            return 1
        if rc is None:
            return 0
        if isinstance(rc, int):
            return rc
        return 0

    # No main(); module may have executed on import.
    print("[modern] Module %s has no main(); assuming import-time "
          "execution." % full)
    return 0


def cmd_samples() -> int:
    return run_module("verify_samples")


def cmd_all() -> int:
    return run_module("build_all")


def cmd_perkey() -> int:
    return run_module("build_per_key")


def cmd_stats() -> int:
    return run_module("build_stats")


def cmd_audit() -> int:
    rc1 = run_module("audit_keys")
    rc2 = run_module("analyze_variety")
    return rc1 or rc2


def cmd_index() -> int:
    ly = os.path.join(MODERN_DIR, "hymn_index.ly")
    if not os.path.exists(ly):
        print("[modern] hymn_index.ly not found at %s" % ly)
        return 1
    if shutil.which("lilypond") is None:
        print("[modern] lilypond not found on PATH.")
        return 1
    print("[modern] Building hymn_index.pdf from %s"
          % os.path.basename(ly))
    try:
        rc = subprocess.call(
            ["lilypond", "-o", "hymn_index", "hymn_index.ly"],
            cwd=MODERN_DIR,
        )
    except OSError as exc:
        print("[modern] lilypond failed: %s" % exc)
        return 1
    if rc == 0:
        pdf = os.path.join(MODERN_DIR, "hymn_index.pdf")
        print("[modern] Wrote %s" % pdf)
    return rc


def cmd_test() -> int:
    modules = [
        "modern.test_reharm_rules",
        "modern.test_voicing_picker",
        "modern.test_abc_rewriter",
        "modern.test_integration",
    ]
    argv = [sys.executable, "-m", "unittest", "-v"] + modules
    try:
        return subprocess.call(argv, cwd=REPO_ROOT)
    except OSError as exc:
        print("[modern] Failed to launch unittest: %s" % exc)
        return 1


# ---------- find ----------

_TEMPO_RE = re.compile(r"Q:\s*[^=\n]*=\s*(\d+)")


def _extract_tempo(abc_text: str) -> str:
    m = _TEMPO_RE.search(abc_text or "")
    if m:
        return m.group(1)
    return "?"


def _clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())


def cmd_find(args) -> int:
    if not args:
        print("Usage: python3.10 -m modern find <title>")
        return 1
    query = " ".join(args).strip().lower()
    if not os.path.exists(LEAD_SHEETS_PATH):
        print("[modern] lead_sheets.json not found at %s"
              % LEAD_SHEETS_PATH)
        return 1
    try:
        with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print("[modern] Failed to load lead_sheets.json: %s" % exc)
        return 1

    entries = []
    for row in data:
        n = str(row.get("n", "")).strip()
        title = _clean_title(row.get("t", ""))
        key = str(row.get("key", "")).strip() or "?"
        tempo = _extract_tempo(row.get("abc", ""))
        entries.append((n, title, key, tempo))

    # Substring match first (case-insensitive).
    matches = [e for e in entries if query in e[1].lower()]
    if not matches:
        titles = [e[1] for e in entries]
        close = difflib.get_close_matches(query, [t.lower() for t in titles],
                                          n=5, cutoff=0.4)
        lower_index = {e[1].lower(): e for e in entries}
        matches = [lower_index[c] for c in close if c in lower_index]

    if not matches:
        print("[modern] No matches for '%s'." % query)
        return 1

    for (n, title, key, tempo) in matches[:5]:
        title_trim = title if len(title) <= 28 else title[:27] + "."
        print("n=%-4s  %-28s  key=%-2s  tempo=%s"
              % (n, title_trim, key, tempo))
    return 0


# ---------- clean ----------

CLEAN_FILES = [
    "samples.pdf", "samples.ly", "samples.ps", "samples.abc",
    "samples_report.md",
    "all_hymns.pdf", "all_hymns.ly",
    "all_hymns_manifest.json", "all_hymns_skipped.json",
    "hymn_index.pdf",
    "variety_report.md",
    "style_proof.pdf", "style_proof.ly",
]

CLEAN_DIRS = ["by_key", "per_hymn"]

CLEAN_GLOB_PREFIXES = ["all_hymns-tmp-"]  # scratch dirs / files


def _collect_clean_targets():
    files = []
    dirs = []
    for name in CLEAN_FILES:
        p = os.path.join(MODERN_DIR, name)
        if os.path.exists(p):
            files.append(p)
    for name in CLEAN_DIRS:
        p = os.path.join(MODERN_DIR, name)
        if os.path.isdir(p):
            dirs.append(p)
    # Glob-prefix scratch.
    try:
        for entry in os.listdir(MODERN_DIR):
            if any(entry.startswith(pref) for pref in CLEAN_GLOB_PREFIXES):
                p = os.path.join(MODERN_DIR, entry)
                if os.path.isdir(p):
                    dirs.append(p)
                elif os.path.isfile(p):
                    files.append(p)
    except OSError:
        pass
    return files, dirs


def cmd_clean(args) -> int:
    skip_prompt = "-y" in args or "--yes" in args
    files, dirs = _collect_clean_targets()
    if not files and not dirs:
        print("[modern] Nothing to clean.")
        return 0
    print("[modern] Would delete:")
    for p in files:
        print("  file  %s" % p)
    for p in dirs:
        print("  dir   %s/" % p)
    if not skip_prompt:
        try:
            ans = input("Proceed? [y/N]: ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print("[modern] Aborted.")
            return 0
    errors = 0
    for p in files:
        try:
            os.remove(p)
        except OSError as exc:
            print("[modern]   rm failed: %s (%s)" % (p, exc))
            errors += 1
    for p in dirs:
        try:
            shutil.rmtree(p)
        except OSError as exc:
            print("[modern]   rmtree failed: %s (%s)" % (p, exc))
            errors += 1
    print("[modern] Clean complete (%d files, %d dirs, %d errors)."
          % (len(files), len(dirs), errors))
    return 1 if errors else 0


# ---------- dispatcher ----------

def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return print_help()

    sub = argv[0].lower()
    rest = argv[1:]

    if sub in ("help", "-h", "--help"):
        return print_help()
    if sub == "samples":
        return cmd_samples()
    if sub == "all":
        return cmd_all()
    if sub == "perkey":
        return cmd_perkey()
    if sub == "index":
        return cmd_index()
    if sub == "stats":
        return cmd_stats()
    if sub == "test":
        return cmd_test()
    if sub == "find":
        return cmd_find(rest)
    if sub == "audit":
        return cmd_audit()
    if sub == "clean":
        return cmd_clean(rest)

    print("[modern] Unknown subcommand: %s" % sub)
    known = [n for n, _ in SUBCOMMANDS]
    close = difflib.get_close_matches(sub, known, n=3, cutoff=0.4)
    if close:
        print("[modern] Did you mean: %s ?" % ", ".join(close))
    print()
    print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
