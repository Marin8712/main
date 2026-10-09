#!/usr/bin/env python3
"""Knapsack instance generator (shared/formats "instance" layout).

Types
  uncorrelated   p_j uniform in [1, R]                       (m = 1)
  weak           p_j uniform in [w_j - R/10, w_j + R/10], >= 1 (m = 1)
  strong         p_j = w_j + R/10                              (m = 1)
  chu-beasley    Chu & Beasley (1998) multidimensional knapsack (any m >= 1)

For the first three, w_j is uniform in [1, R] and the capacity is
floor(capacity_ratio * sum_j w_j).  For chu-beasley, a_ij is uniform in
[0, 1000], b_i = floor(tightness * sum_j a_ij) and
p_j = round(sum_i a_ij / m + 500 * q_j) with q_j uniform in (0, 1).

Determinism: only random.Random(seed).randint()/random() are used, drawn in a
fixed order, and the output contains no timestamps, so the same arguments give
byte-identical files.  Draw order: all weights (constraint-major), then for
each item the profit draw.

Usage
  generate.py --type strong --n 100 --seed 42 --out inst.json
  generate.py --type chu-beasley --n 100 --m 5 --tightness 0.25 --seed 1 --out inst.json
  generate.py --type weak --n 50 --seed 7 --count 20 --out-dir data/instances
"""
import argparse
import json
import random
import sys
from pathlib import Path

TYPES = ("uncorrelated", "weak", "strong", "chu-beasley")
SINGLE_CONSTRAINT_TYPES = ("uncorrelated", "weak", "strong")
CB_WEIGHT_MAX = 1000
DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "instances"


def _single(type_, n, rng, rng_range, capacity_ratio):
    weights = [rng.randint(1, rng_range) for _ in range(n)]
    delta = rng_range // 10
    if type_ == "uncorrelated":
        profits = [rng.randint(1, rng_range) for _ in range(n)]
    elif type_ == "weak":
        profits = [max(1, rng.randint(w - delta, w + delta)) for w in weights]
    else:
        profits = [w + delta for w in weights]
    capacity = max(1, int(capacity_ratio * sum(weights)))
    return profits, [weights], [capacity]


def _chu_beasley(n, m, rng, tightness):
    a = [[rng.randint(0, CB_WEIGHT_MAX) for _ in range(n)] for _ in range(m)]
    profits = []
    for j in range(n):
        col = sum(a[i][j] for i in range(m))
        profits.append(int(round(col / m + 500 * rng.random())))
    caps = [int(tightness * sum(row)) for row in a]
    return profits, a, caps


def generate(type_, n, m=1, seed=0, rng_range=1000, capacity_ratio=0.5,
             tightness=0.5, instance_id=None):
    if type_ not in TYPES:
        raise ValueError(f"unknown type {type_!r}; choose from {TYPES}")
    if n < 1 or m < 1:
        raise ValueError("n and m must be >= 1")
    if type_ in SINGLE_CONSTRAINT_TYPES and m != 1:
        raise ValueError(f"type {type_!r} only supports m = 1; use chu-beasley for m > 1")
    rng = random.Random(seed)
    meta = {"source": "generated", "seed": seed, "generator": type_, "n": n, "m": m}
    if type_ == "chu-beasley":
        profits, weights, caps = _chu_beasley(n, m, rng, tightness)
        meta["tightness"] = tightness
        meta["variant"] = "mkp" if m > 1 else "knapsack"
    else:
        profits, weights, caps = _single(type_, n, rng, rng_range, capacity_ratio)
        meta["range"] = rng_range
        meta["capacity_ratio"] = capacity_ratio
        meta["variant"] = "knapsack"
    if instance_id is None:
        instance_id = f"knapsack-{type_}-n{n}-m{m}-s{seed}"
    names = [f"x{j + 1}" for j in range(n)]
    constraints = []
    for i in range(m):
        terms = {names[j]: weights[i][j] for j in range(n) if weights[i][j] != 0}
        constraints.append({
            "name": "capacity" if m == 1 else f"capacity{i + 1}",
            "terms": terms, "op": "<=", "rhs": caps[i],
        })
    return {
        "id": instance_id,
        "family": "knapsack",
        "sense": "max",
        "variables": [{"name": names[j], "type": "binary", "objective": profits[j]}
                      for j in range(n)],
        "constraints": constraints,
        "meta": meta,
    }


def _compact(obj):
    return json.dumps(obj, separators=(", ", ": "))


def dumps(inst):
    """Fixed layout, one variable / constraint per line, trailing newline."""
    out = ["{"]
    out.append(f'  "id": {json.dumps(inst["id"])},')
    out.append(f'  "family": {json.dumps(inst["family"])},')
    out.append(f'  "sense": {json.dumps(inst["sense"])},')
    for key in ("variables", "constraints"):
        out.append(f'  "{key}": [')
        out.append(",\n".join("    " + _compact(e) for e in inst[key]))
        out.append("  ],")
    out.append(f'  "meta": {_compact(inst["meta"])}')
    out.append("}")
    return "\n".join(out) + "\n"


def _parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--type", choices=TYPES, default="uncorrelated")
    p.add_argument("--n", type=int, required=True, help="number of items")
    p.add_argument("--m", type=int, default=1, help="number of constraints (chu-beasley only when > 1)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--range", dest="rng_range", type=int, default=1000, help="R for uncorrelated/weak/strong")
    p.add_argument("--capacity-ratio", type=float, default=0.5, help="capacity / total weight (single-constraint types)")
    p.add_argument("--tightness", type=float, default=0.5, help="alpha for chu-beasley (OR-Library uses 0.25, 0.5, 0.75)")
    p.add_argument("--id", dest="instance_id", help="instance id (default derived from the parameters)")
    p.add_argument("--out", help="output file (default: stdout)")
    p.add_argument("--count", type=int, default=1, help="write seeds seed..seed+count-1 into --out-dir")
    p.add_argument("--out-dir", help=f"output directory for --count (default {DEFAULT_OUT_DIR})")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    kw = dict(n=args.n, m=args.m, rng_range=args.rng_range,
              capacity_ratio=args.capacity_ratio, tightness=args.tightness)
    try:
        if args.count > 1 or args.out_dir:
            if args.out or args.instance_id:
                sys.exit("--out/--id cannot be combined with --count/--out-dir")
            out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_OUT_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            for s in range(args.seed, args.seed + args.count):
                inst = generate(args.type, seed=s, **kw)
                (out_dir / f"{inst['id']}.json").write_text(dumps(inst))
            print(f"wrote {args.count} instance(s) to {out_dir}", file=sys.stderr)
            return
        inst = generate(args.type, seed=args.seed, instance_id=args.instance_id, **kw)
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    text = dumps(inst)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
