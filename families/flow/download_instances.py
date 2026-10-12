#!/usr/bin/env python3
"""Download flow benchmark instances (DIMACS network-flow archive).

Files go to ./instances/<source>/ next to this script. That directory is
git-ignored; downloaded data must never be committed.

Usage: download_instances.py [SOURCE ...]            (default: all sources)
       download_instances.py --url URL [--url URL]   (extra files, saved under instances/extra/)

The file lists below are the part to edit: the DIMACS archive publishes
generators and a few data sets, and the exact file names were not verified
(the default entry only fetches the archive's directory page so you can pick
files from it and add them to DIMACS_FILES or pass them with --url).
"""
import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DIMACS_BASE = "http://archive.dimacs.rutgers.edu/pub/netflow/"
DIMACS_FILES = ["index.html"]       # add e.g. "mincost/<file>" / "maxflow/<file>" here

SOURCES = {"dimacs": (DIMACS_BASE, DIMACS_FILES)}
OUT_ROOT = Path(__file__).resolve().parent / "instances"


def fetch(url: str, dest: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  FAILED {url}: {exc}", file=sys.stderr)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  ok     {dest.name} ({len(data)} bytes)")
    return True


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sources", nargs="*", help=f"one of {', '.join(SOURCES)} (default: all)")
    ap.add_argument("--url", action="append", default=[], help="additional file URL")
    args = ap.parse_args(argv)
    unknown = [n for n in args.sources if n not in SOURCES]
    if unknown:
        print(f"unknown source(s): {', '.join(unknown)}; choose from {', '.join(SOURCES)}", file=sys.stderr)
        return 2
    names = args.sources or ([] if args.url else list(SOURCES))

    failures = 0
    for name in names:
        base, files = SOURCES[name]
        out_dir = OUT_ROOT / name
        print(f"{name} -> {out_dir}")
        for fname in files:
            failures += not fetch(base + fname, out_dir / Path(fname).name)
    for url in args.url:
        fname = Path(urllib.parse.urlparse(url).path).name or "download"
        print(f"extra -> {OUT_ROOT / 'extra'}")
        failures += not fetch(url, OUT_ROOT / "extra" / fname)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
