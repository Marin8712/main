#!/usr/bin/env python3
"""Convert DIMACS network-flow files into shared/formats instance JSON.

Supported problem lines
  p min N M     a i j low cap cost      n i supply      (minimum-cost flow)
  p max N M     a i j cap               n i s | n i t   (maximum flow)
A max-flow file becomes an MCF with the return arc t -> s of cost -1 and no
capacity (original value = -objective, meta.objective_sign = -1).  Lines
starting with c are comments.  Parallel arcs get a suffix: x_i_j, x_i_j_2, ...
A lower bound > 0 adds a row low_i_j: x_i_j >= low.

Best-known optimum values are not in the DIMACS files; pass them with
--best-known CSV (lines "instance_id,value", value in the ORIGINAL problem's
terms, e.g. the max-flow value).  The id is dimacs-<file stem>.

Usage
  dimacs_to_json.py [FILE ...] [--out-dir DIR] [--best-known CSV]
Default FILEs: every file in instances/dimacs (see ../download_instances.py);
files that are not DIMACS flow files are skipped with a warning.
Run it with `python3 -I`: the input files are downloaded data.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

FAMILY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IN = FAMILY_DIR / "instances" / "dimacs"
DEFAULT_OUT = FAMILY_DIR / "data" / "instances" / "dimacs"


def _num(tok):
    try:
        return int(tok)
    except ValueError:
        return float(tok)


def parse(text, stem):
    kind = n = m_decl = None
    b, s, t = {}, None, None
    arcs = []                       # (i, j, cost, cap_or_None, low)
    for lineno, line in enumerate(text.splitlines(), 1):
        tok = line.split()
        if not tok or tok[0] == "c":
            continue
        try:
            if tok[0] == "p":
                kind, n, m_decl = tok[1], int(tok[2]), int(tok[3])
                if kind not in ("min", "max"):
                    raise ValueError(f"unsupported problem type {kind!r}")
            elif kind is None:
                raise ValueError("line before the 'p' line")
            elif tok[0] == "n":
                node = int(tok[1])
                if kind == "min":
                    b[node] = _num(tok[2])
                elif tok[2] == "s":
                    s = node
                elif tok[2] == "t":
                    t = node
                else:
                    raise ValueError(f"bad node designator {tok[2]!r}")
            elif tok[0] == "a":
                i, j = int(tok[1]), int(tok[2])
                if kind == "min":
                    arcs.append((i, j, _num(tok[5]), _num(tok[4]), _num(tok[3])))
                else:
                    arcs.append((i, j, 0, _num(tok[3]), 0))
            else:
                raise ValueError(f"unknown line type {tok[0]!r}")
        except (IndexError, ValueError) as exc:
            raise ValueError(f"{stem}:{lineno}: {exc}") from None
    if kind is None:
        raise ValueError(f"{stem}: no 'p' line")
    if len(arcs) != m_decl:
        raise ValueError(f"{stem}: declared {m_decl} arcs, found {len(arcs)}")
    supply = [b.get(v, 0) for v in range(1, n + 1)]
    meta = {"source": "dimacs", "file": stem, "n": n, "m": len(arcs), "variant": kind}
    if kind == "min":
        if sum(supply) != 0:
            raise ValueError(f"{stem}: supplies sum to {sum(supply)}, expected 0")
    else:
        if s is None or t is None:
            raise ValueError(f"{stem}: max-flow file needs 'n i s' and 'n i t' lines")
        arcs.append((t, s, -1, None, 0))
        meta.update(source_node=s, sink_node=t, original="max-flow", objective_sign=-1)
        meta["m"] = len(arcs)
    return build(f"dimacs-{stem}", n, arcs, supply, meta)


def build(inst_id, n, arcs, b, meta):
    names, seen = [], {}
    for i, j, _, _, _ in arcs:
        seen[(i, j)] = seen.get((i, j), 0) + 1
        k = seen[(i, j)]
        names.append(f"x_{i}_{j}" if k == 1 else f"x_{i}_{j}_{k}")
    tags = [nm[2:] for nm in names]
    out_arcs = {v: [] for v in range(1, n + 1)}
    in_arcs = {v: [] for v in range(1, n + 1)}
    for nm, (i, j, _, _, _) in zip(names, arcs):
        out_arcs[i].append(nm)
        in_arcs[j].append(nm)
    cons = []
    for v in range(1, n + 1):
        terms = {nm: 1 for nm in out_arcs[v]}
        terms.update({nm: -1 for nm in in_arcs[v]})
        cons.append({"name": f"node_{v}", "terms": terms, "op": "==", "rhs": b[v - 1]})
    for nm, tag, (_, _, _, cap, _) in zip(names, tags, arcs):
        if cap is not None:
            cons.append({"name": f"cap_{tag}", "terms": {nm: 1}, "op": "<=", "rhs": cap})
    for nm, tag, (_, _, _, _, low) in zip(names, tags, arcs):
        if low:
            cons.append({"name": f"low_{tag}", "terms": {nm: 1}, "op": ">=", "rhs": low})
    return {"id": inst_id, "family": "flow", "sense": "min",
            "variables": [{"name": nm, "type": "real", "objective": a[2]} for nm, a in zip(names, arcs)],
            "constraints": cons, "meta": meta}


def dumps(inst):
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
    ap.add_argument("--best-known", type=Path, help="CSV of instance_id,value")
    args = ap.parse_args(argv)
    files = args.files or sorted(p for p in DEFAULT_IN.glob("*") if p.is_file())
    if not files:
        sys.exit(f"no input files (run ../download_instances.py first, looked in {DEFAULT_IN})")
    known = {}
    if args.best_known:
        with open(args.best_known, newline="") as fh:
            known = {r[0].strip(): _num(r[1].strip()) for r in csv.reader(fh) if len(r) >= 2 and r[0].strip()}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    total = skipped = 0
    for f in files:
        try:
            inst = parse(f.read_text(errors="replace"), f.stem)
        except ValueError as exc:
            print(f"skipping {f.name}: {exc}", file=sys.stderr)
            skipped += 1
            continue
        if inst["id"] in known:
            inst["meta"]["best_known"] = known[inst["id"]]
        (args.out_dir / f"{inst['id']}.json").write_text(dumps(inst))
        total += 1
    print(f"wrote {total} instance(s) to {args.out_dir}, skipped {skipped}", file=sys.stderr)
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
