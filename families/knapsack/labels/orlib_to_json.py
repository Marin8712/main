#!/usr/bin/env python3
"""Convert OR-Library multidimensional knapsack files (mknap1/2, mknapcb1-9)
into shared/formats instance JSON, one file per problem.

File layout (whitespace separated): K, then for each of K problems
  n  m  best_known(0 = unknown)
  p_1 .. p_n
  m rows of n weights
  b_1 .. b_m

The header value is stored as meta.best_known when it is > 0.  The mknapcb
headers are usually 0, so the best-known values can be given with
--best-known CSV (lines "instance_id,value", e.g. "orlib-mknapcb1-01,24381").

Usage
  orlib_to_json.py [FILE ...] [--out-dir DIR] [--best-known CSV]
Default FILEs: instances/orlib/*.txt (see ../download_instances.py)
Run it with `python3 -I`: the input files are downloaded data.
"""
import argparse
import csv
import sys
from pathlib import Path

FAMILY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IN = FAMILY_DIR / "instances" / "orlib"
DEFAULT_OUT = FAMILY_DIR / "data" / "instances" / "orlib"


def _num(tok):
    try:
        return int(tok)
    except ValueError:
        return float(tok)


def parse(text, stem):
    """Yield instance dicts for every problem in an OR-Library MKP file."""
    tok = text.split()
    pos = 0

    def take(k):
        nonlocal pos
        if pos + k > len(tok):
            raise ValueError(f"{stem}: file ends early (need {k} more values at token {pos})")
        out = [_num(t) for t in tok[pos:pos + k]]
        pos += k
        return out

    (k,) = take(1)
    for idx in range(1, k + 1):
        n, m, best = take(3)
        profits = take(n)
        rows = [take(n) for _ in range(m)]
        caps = take(m)
        names = [f"x{j + 1}" for j in range(n)]
        meta = {"source": "orlib", "file": stem, "index": idx, "n": n, "m": m,
                "variant": "mkp" if m > 1 else "knapsack"}
        if best > 0:
            meta["best_known"] = best
        yield {
            "id": f"orlib-{stem}-{idx:02d}",
            "family": "knapsack",
            "sense": "max",
            "variables": [{"name": nm, "type": "binary", "objective": p} for nm, p in zip(names, profits)],
            "constraints": [{"name": "capacity" if m == 1 else f"capacity{i + 1}",
                             "terms": {nm: w for nm, w in zip(names, rows[i]) if w != 0},
                             "op": "<=", "rhs": caps[i]} for i in range(m)],
            "meta": meta,
        }
    if pos != len(tok):
        raise ValueError(f"{stem}: {len(tok) - pos} unexpected trailing values")


def dumps(inst):
    import json
    c = lambda o: json.dumps(o, separators=(", ", ": "))
    body = [f'  "id": {json.dumps(inst["id"])},', f'  "family": "{inst["family"]}",', f'  "sense": "{inst["sense"]}",']
    for key in ("variables", "constraints"):
        body += [f'  "{key}": [', ",\n".join("    " + c(e) for e in inst[key]), "  ],"]
    body.append(f'  "meta": {c(inst["meta"])}')
    return "{\n" + "\n".join(body) + "\n}\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--best-known", type=Path, help="CSV of instance_id,value overriding the file header")
    args = ap.parse_args(argv)
    files = args.files or sorted(DEFAULT_IN.glob("*.txt"))
    if not files:
        sys.exit(f"no input files (run ../download_instances.py first, looked in {DEFAULT_IN})")
    known = {}
    if args.best_known:
        with open(args.best_known, newline="") as fh:
            known = {r[0].strip(): _num(r[1].strip()) for r in csv.reader(fh) if len(r) >= 2 and r[0].strip()}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for f in files:
        for inst in parse(f.read_text(), f.stem):
            if inst["id"] in known:
                inst["meta"]["best_known"] = known[inst["id"]]
            (args.out_dir / f"{inst['id']}.json").write_text(dumps(inst))
            total += 1
    print(f"wrote {total} instance(s) to {args.out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
