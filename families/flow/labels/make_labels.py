#!/usr/bin/env python3
"""Solve flow instances with Gurobi and save the full label record for each.

Flow problems are pure LPs (real variables; the constraint matrix is totally
unimodular, so integer data gives an integral optimum), so there is no
branch-and-bound and no sequence of improving solutions.  For every instance
JSON one <id>.label.json is written with
  * the optimal solution x, objective, reduced costs, the dual value (Pi) of
    every constraint (node potentials for the node_i rows, capacity duals for
    the cap_i_j rows) and slacks, plus status, iterations and solve time
  * original_objective: the objective mapped back to the original problem
    (meta.objective_sign, e.g. -1 turns the max-flow reduction back into the
    max-flow value)
  * the Gurobi version and parameters, and the instance SHA-256
The record keeps the same top-level layout as the knapsack labels
(lp_relaxation holds the solve, mip is null) so consumers can treat families
alike.

All vectors follow the order of "variables" / "constraints" in the instance;
the names are repeated once at the top of the label.  Sign convention
(minimisation): node row duals are free, cap_i_j duals are <= 0, and
objective = sum_i Pi_i * b_i + sum_ij Pi_cap_ij * u_ij.

Usage
  make_labels.py PATH [PATH ...] [--out-dir DIR] [--time-limit S] [--method M]
PATH is an instance file or a directory of *.json instances.
If an instance has meta.best_known (DIMACS conversions can carry it) the
original objective must match it: an optimal LP result that differs makes the
exit status 1, as does any failed instance.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

FAMILY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IN = FAMILY_DIR / "data" / "instances"
DEFAULT_OUT = FAMILY_DIR / "data" / "labels"
SENSE = {"max": GRB.MAXIMIZE, "min": GRB.MINIMIZE}
OPS = {"<=": GRB.LESS_EQUAL, ">=": GRB.GREATER_EQUAL, "=": GRB.EQUAL, "==": GRB.EQUAL}
STATUS_NAMES = {GRB.LOADED: "LOADED", GRB.OPTIMAL: "OPTIMAL", GRB.INFEASIBLE: "INFEASIBLE",
                GRB.INF_OR_UNBD: "INF_OR_UNBD", GRB.UNBOUNDED: "UNBOUNDED", GRB.CUTOFF: "CUTOFF",
                GRB.ITERATION_LIMIT: "ITERATION_LIMIT", GRB.NODE_LIMIT: "NODE_LIMIT",
                GRB.TIME_LIMIT: "TIME_LIMIT", GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
                GRB.INTERRUPTED: "INTERRUPTED", GRB.NUMERIC: "NUMERIC", GRB.SUBOPTIMAL: "SUBOPTIMAL"}


def build_model(inst, args):
    m = gp.Model(inst["id"])
    m.Params.OutputFlag = 1 if args.verbose else 0
    m.Params.Threads = args.threads
    m.Params.Seed = args.seed
    vs = []
    for v in inst["variables"]:
        if v["type"] != "real":
            raise ValueError(f"variable {v['name']}: flow labels are LP-only, got type {v['type']!r}")
        vs.append(m.addVar(lb=v.get("lb", 0.0), ub=v.get("ub", GRB.INFINITY), obj=v["objective"]))
    by_name = {spec["name"]: v for spec, v in zip(inst["variables"], vs)}
    cs = []
    for c in inst["constraints"]:
        expr = gp.LinExpr([(coef, by_name[n]) for n, coef in c["terms"].items()])
        cs.append(m.addLConstr(expr, OPS[c["op"]], c["rhs"], name=c["name"]))
    m.ModelSense = SENSE[inst["sense"]]
    m.update()
    return m, vs, cs


def _status(code):
    return STATUS_NAMES.get(code, str(code))


def lp_record(inst, args):
    m, vs, cs = build_model(inst, args)
    m.Params.Method = args.method
    m.Params.Presolve = 0 if args.method in (0, 1) else -1   # basic solution, clean duals
    if args.time_limit is not None:
        m.Params.TimeLimit = args.time_limit
    m.optimize()
    rec = {"status": _status(m.Status), "time_s": m.Runtime,
           "iterations": int(m.IterCount), "barrier_iterations": int(m.BarIterCount),
           "time_limit_hit": m.Status == GRB.TIME_LIMIT,
           "objective": None, "x": None, "reduced_costs": None, "duals": None, "slacks": None}
    if m.Status == GRB.OPTIMAL:
        rec.update(objective=m.ObjVal,
                   x=[v.X for v in vs],
                   reduced_costs=[v.RC for v in vs],
                   duals=[c.Pi for c in cs],
                   slacks=[c.Slack for c in cs])
    return rec


def make_label(path, args):
    raw = Path(path).read_bytes()
    inst = json.loads(raw)
    meta = inst.get("meta", {})
    lp = lp_record(inst, args)
    label = {
        "instance_id": inst["id"],
        "instance_sha256": hashlib.sha256(raw).hexdigest(),
        "family": inst["family"],
        "sense": inst["sense"],
        "gurobi": {"version": ".".join(map(str, gp.gurobi.version())), "threads": args.threads,
                   "seed": args.seed, "method": args.method, "time_limit_s": args.time_limit},
        "variables": [v["name"] for v in inst["variables"]],
        "constraints": [c["name"] for c in inst["constraints"]],
        "lp_relaxation": lp,
        "mip": None,
        "original_objective": (None if lp["objective"] is None
                               else meta.get("objective_sign", 1) * lp["objective"]),
    }
    if "best_known" in meta:
        label["best_known"] = meta["best_known"]
    return label


def check_best_known(label):
    """Return (text, ok); an optimal LP value must equal best_known."""
    bk, obj = label.get("best_known"), label["original_objective"]
    if bk is None:
        return "", True
    if obj is None:
        return "best_known=%g, no solution" % bk, True
    if abs(obj - bk) <= 1e-6 * (1 + abs(bk)):
        return "= best_known %g" % bk, True
    return "!= best_known %g (%+g)" % (bk, obj - bk), False


def collect(paths):
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.glob("*.json") if not f.name.endswith(".label.json"))
        else:
            files.append(p)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_IN], help=f"instance files/dirs (default {DEFAULT_IN})")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--time-limit", type=float, default=None, help="LP time limit in seconds")
    ap.add_argument("--method", type=int, default=1, choices=[-1, 0, 1, 2],
                    help="Gurobi Method: 0 primal, 1 dual simplex (default), 2 barrier, -1 automatic")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="show the Gurobi log")
    args = ap.parse_args(argv)

    files = collect(args.paths)
    if not files:
        sys.exit("no instance files found")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    print(f"{'instance':40} {'objective':>14} {'original':>14} {'status':>9} {'iters':>7} {'time[s]':>8}")
    for f in files:
        out = args.out_dir / (json.loads(f.read_bytes())["id"] + ".label.json")
        if args.skip_existing and out.exists():
            continue
        try:
            label = make_label(f, args)
        except (gp.GurobiError, KeyError, ValueError) as exc:
            print(f"{f.name}: FAILED: {exc}", file=sys.stderr)
            failed += 1
            continue
        out.write_text(json.dumps(label, indent=1) + "\n")
        lp = label["lp_relaxation"]
        fmt = lambda x: "-" if x is None else f"{x:.8g}"
        note, ok = check_best_known(label)
        failed += not ok
        print(f"{label['instance_id']:40} {fmt(lp['objective']):>14} {fmt(label['original_objective']):>14} "
              f"{lp['status']:>9} {lp['iterations']:7d} {lp['time_s']:8.3f}  {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
