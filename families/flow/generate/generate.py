#!/usr/bin/env python3
"""Flow instance generator (shared/formats "instance" layout).

Everything is emitted as a minimum-cost flow (MCF) following the reduction map:

  mcf             random network, supplies b_i, capacities u_ij, costs c_ij
  transportation  complete bipartite network, supplies/demands, no capacities
  shortest-path   one unit from node 1 to node n, no capacities, costs >= 1
  max-flow        capacities only; return arc n -> 1 with cost -1 and no
                  capacity, all other costs 0 and all supplies 0
                  (original max flow value = -objective, see meta.objective_sign)

Encoding: one real variable x_i_j per arc (objective = cost), one equality row
node_i per node (out-flow minus in-flow = b_i) and one row cap_i_j: x_i_j <= u_ij
per capacitated arc.  Nodes are numbered 1..n.

Feasibility: mcf gets a backbone cycle 1 -> 2 -> ... -> n -> 1 whose capacity is
the total supply T and whose cost is 2 * max_cost, so any supply/demand pattern
can be routed.  shortest-path and max-flow get a backbone path 1 -> ... -> n.

Determinism: only random.Random(seed).randint()/sample() are used, drawn in a
fixed order (terminals, supply split, demand split, extra arcs, then per arc
capacity and cost), and the output has no timestamps, so the same arguments
give byte-identical files.

Usage
  generate.py --type mcf --n 50 --m 200 --seed 42 --out inst.json
  generate.py --type transportation --n 20 --seed 1 --count 10 --out-dir data/instances
"""
import argparse
import json
import random
import sys
from pathlib import Path

TYPES = ("mcf", "transportation", "shortest-path", "max-flow")
DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "instances"


def _split(rng, total, k):
    """Random composition of `total` into k positive integers."""
    if total < k:
        raise ValueError(f"cannot split {total} into {k} positive parts")
    if k == 1:
        return [total]
    cuts = sorted(rng.sample(range(1, total), k - 1))
    return [b - a for a, b in zip([0] + cuts, cuts + [total])]


def _extra_arcs(rng, n, count, used):
    """`count` new distinct arcs (i, j), i != j, not in `used`."""
    free = n * (n - 1) - len(used)
    if count > free:
        raise ValueError(f"asked for {count} extra arcs but only {free} are free (n={n})")
    taken, out = set(used), []
    if 2 * count <= free:
        while len(out) < count:
            i, j = rng.randint(1, n), rng.randint(1, n)
            if i != j and (i, j) not in taken:
                taken.add((i, j))
                out.append((i, j))
        return out
    cand = [(i, j) for i in range(1, n + 1) for j in range(1, n + 1) if i != j and (i, j) not in taken]
    return rng.sample(cand, count)


def build(inst_id, n, arcs, b, meta, sense="min"):
    """arcs: list of (i, j, cost, cap_or_None); b: supply per node 1..n."""
    names = [f"x_{i}_{j}" for i, j, _, _ in arcs]
    out_arcs = {v: [] for v in range(1, n + 1)}
    in_arcs = {v: [] for v in range(1, n + 1)}
    for name, (i, j, _, _) in zip(names, arcs):
        out_arcs[i].append(name)
        in_arcs[j].append(name)
    constraints = []
    for v in range(1, n + 1):
        terms = {nm: 1 for nm in out_arcs[v]}
        terms.update({nm: -1 for nm in in_arcs[v]})
        constraints.append({"name": f"node_{v}", "terms": terms, "op": "==", "rhs": b[v - 1]})
    for name, (i, j, _, cap) in zip(names, arcs):
        if cap is not None:
            constraints.append({"name": f"cap_{i}_{j}", "terms": {name: 1}, "op": "<=", "rhs": cap})
    return {
        "id": inst_id,
        "family": "flow",
        "sense": sense,
        "variables": [{"name": nm, "type": "real", "objective": c} for nm, (_, _, c, _) in zip(names, arcs)],
        "constraints": constraints,
        "meta": meta,
    }


def generate(type_, n, m=None, seed=0, max_cap=100, max_cost=100, supply_total=None,
             instance_id=None):
    if type_ not in TYPES:
        raise ValueError(f"unknown type {type_!r}; choose from {TYPES}")
    if n < 2:
        raise ValueError("n must be >= 2")
    rng = random.Random(seed)
    meta = {"source": "generated", "seed": seed, "generator": type_, "n": n}

    if type_ == "transportation":
        if m is not None:
            raise ValueError("transportation uses the complete bipartite network; omit --m")
        s, t = n // 2, n - n // 2
        total = supply_total if supply_total is not None else 50 * max(s, t)
        sup, dem = _split(rng, total, s), _split(rng, total, t)
        b = sup + [-d for d in dem]
        arcs = [(i, s + j, rng.randint(1, max_cost), None)
                for i in range(1, s + 1) for j in range(1, t + 1)]
        meta.update(m=len(arcs), sources=s, sinks=t, supply_total=total, max_cost=max_cost)
    else:
        m = 4 * n if m is None else m
        b = [0] * n
        if type_ == "mcf":
            if m < n:
                raise ValueError("mcf needs m >= n (backbone cycle)")
            k = max(1, n // 10)
            total = supply_total if supply_total is not None else max(k, k * max_cap // 2)
            terminals = rng.sample(range(1, n + 1), 2 * k)
            for node, v in zip(terminals[:k], _split(rng, total, k)):
                b[node - 1] = v
            for node, v in zip(terminals[k:], _split(rng, total, k)):
                b[node - 1] = -v
            back = [(i, i % n + 1) for i in range(1, n + 1)]
            extra = _extra_arcs(rng, n, m - n, set(back))
            arcs = [(i, j, 2 * max_cost, total) for i, j in back]
            for i, j in extra:
                cap = rng.randint(1, max_cap)
                arcs.append((i, j, rng.randint(1, max_cost), cap))
            meta.update(m=m, max_cap=max_cap, max_cost=max_cost, supply_total=total, terminals=k)
        else:
            if m < n - 1:
                raise ValueError(f"{type_} needs m >= n - 1 (backbone path)")
            back = [(i, i + 1) for i in range(1, n)]
            forbidden = set(back) | ({(n, 1)} if type_ == "max-flow" else set())
            extra = _extra_arcs(rng, n, m - (n - 1) - (1 if type_ == "max-flow" else 0), forbidden)
            if type_ == "shortest-path":
                b[0], b[n - 1] = 1, -1
                arcs = [(i, j, rng.randint(1, max_cost), None) for i, j in back + extra]
                meta.update(m=m, max_cost=max_cost, source=1, sink=n)
            else:
                arcs = [(i, j, 0, rng.randint(1, max_cap)) for i, j in back + extra]
                arcs.append((n, 1, -1, None))
                meta.update(m=m, max_cap=max_cap, source=1, sink=n, original="max-flow",
                            objective_sign=-1)
    meta["variant"] = type_
    if instance_id is None:
        instance_id = f"flow-{type_}-n{n}-m{meta['m']}-s{seed}"
    return build(instance_id, n, arcs, b, meta)


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
    p.add_argument("--type", choices=TYPES, default="mcf")
    p.add_argument("--n", type=int, required=True, help="number of nodes")
    p.add_argument("--m", type=int, default=None, help="number of arcs (default 4n; not for transportation)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-cap", type=int, default=100, help="capacities uniform in [1, max-cap]")
    p.add_argument("--max-cost", type=int, default=100, help="costs uniform in [1, max-cost]")
    p.add_argument("--supply-total", type=int, default=None, help="total supply (mcf, transportation)")
    p.add_argument("--id", dest="instance_id", help="instance id (default derived from the parameters)")
    p.add_argument("--out", help="output file (default: stdout)")
    p.add_argument("--count", type=int, default=1, help="write seeds seed..seed+count-1 into --out-dir")
    p.add_argument("--out-dir", help=f"output directory for --count (default {DEFAULT_OUT_DIR})")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    kw = dict(n=args.n, m=args.m, max_cap=args.max_cap, max_cost=args.max_cost,
              supply_total=args.supply_total)
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
