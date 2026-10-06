#!/usr/bin/env python3
"""Download the Pisinger and OR-Library knapsack instances.

Files go to ./instances/<source>/ next to this script. That directory is
git-ignored; downloaded data must never be committed.

Usage: download_instances.py [orlib|pisinger ...]   (default: all)
"""
import sys
import urllib.error
import urllib.request
from pathlib import Path

ORLIB_BASE = "http://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/"
ORLIB_FILES = ["mknap1.txt", "mknap2.txt"] + [f"mknapcb{i}.txt" for i in range(1, 10)]

PISINGER_BASE = "https://hjemmesider.diku.dk/~pisinger/"
# Add direct links to instance files/archives from the page below as needed.
PISINGER_FILES = ["codes.html"]

SOURCES = {
    "orlib": (ORLIB_BASE, ORLIB_FILES),
    "pisinger": (PISINGER_BASE, PISINGER_FILES),
}

OUT_ROOT = Path(__file__).resolve().parent / "instances"


def fetch(url: str, dest: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  FAILED {url}: {exc}", file=sys.stderr)
        return False
    dest.write_bytes(data)
    print(f"  ok     {dest.name} ({len(data)} bytes)")
    return True


def main(argv: list[str]) -> int:
    names = argv or list(SOURCES)
    unknown = [n for n in names if n not in SOURCES]
    if unknown:
        print(f"unknown source(s): {', '.join(unknown)}; choose from {', '.join(SOURCES)}", file=sys.stderr)
        return 2

    failures = 0
    for name in names:
        base, files = SOURCES[name]
        out_dir = OUT_ROOT / name
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"{name} -> {out_dir}")
        for fname in files:
            if not fetch(base + fname, out_dir / fname):
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
