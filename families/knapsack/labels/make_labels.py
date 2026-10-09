#!/usr/bin/env python3
"""Solve instances with Gurobi and save the full label record for each.

For every instance JSON (shared/formats "instance") one <id>.label.json is
written with
  * the LP relaxation: objective, primal values, reduced costs and the dual
    value (Pi) of every constraint, i.e. of each capacity constraint for MKP
  * the MIP: final solution, objective, best bound, final gap, node count,
    solve time, status, and every improving solution (MIPSOL callback) with
    the time it was found
  * the Gurobi version and the parameters used, and the instance SHA-256

All vectors are aligned with the order of "variables" / "constraints" in the
instance; the names are repeated once at the top of the label.  Duals and
reduced costs use Gurobi's convention for the instance's own sense (for max:
Pi >= 0 on <= rows, RC > 0 for a variable sitting at its upper bound).

Usage
  make_labels.py PATH [PATH ...] [--out-dir DIR] [--time-limit S]
PATH is an instance file or a directory of *.json instances.
If an instance has meta.best_known (OR-Library files do) the result is
compared against it.  Exit status is 1 if any instance failed or an optimal
solve came out below the best-known value.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

FAMILY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_IN = FAMILY_DIR / "data" / "instances"
DEFAULT_OUT = FAMILY_DIR / "data" / "labels"
VTYPE = {"binary": GRB.BINARY, "integer": GRB.INTEGER, "real": GRB.CONTINUOUS}
SENSE = {"max": GRB.MAXIMIZE, "min": GRB.MINIMIZE}
OPS = {"<=": GRB.LESS_EQUAL, ">=": GRB.GREATER_EQUAL, "=": GRB.EQUAL, "==": GRB.EQUAL}


def build_model(inst, threads, seed, verbose=False):
    m = gp.Model(inst["id"])
    m.Params.OutputFlag = 1 if verbose else 0
    m.Params.Threads = threads
    m.Params.Seed = seed
    vs = []
    for v in inst["variables"]:
        t = v["type"]
        if t not in VTYPE:
            raise ValueError(f"variable {v['name']}: unknown type {t!r}")
        lb = v.get("lb", 0.0)
        ub = v.get("ub", 1.0 if t == "binary" else GRB.INFINITY)
        vs.append(m.addVar(lb=lb, ub=ub, obj=v["objective"], vtype=VTYPE[t], name=v["name"]))
    by_name = {spec["name"]: v for spec, v in zip(inst["variables"], vs)}
    cs = []
    for c in inst["constraints"]:
        expr = gp.LinExpr([(coef, by_name[n]) for n, coef in c["terms"].items()])
        cs.append(m.addLConstr(expr, OPS[c["op"]], c["rhs"], name=c["name"]))
    m.ModelSense = SENSE[inst["sense"]]
    m.update()
    return m, vs, cs


def lp_record(inst, args):
    m, vs, cs = build_model(inst, args.threads, args.seed)
    lp = m.relax()
    lp.Params.Method = 1          # dual simplex -> basic solution, clean duals
    lp.Params.Presolve = 0
    lp.optimize()
    rec = {"status": _status(lp.Status), "time_s": lp.Runtime}
    if lp.Status == GRB.OPTIMAL:
        lvars, lcons = lp.getVars(), lp.getConstrs()
        rec.update(objective=lp.ObjVal,
                   x=[v.X for v in lvars],
                   reduced_costs=[v.RC for v in lvars],
                   duals=[c.Pi for c in lcons],
                   slacks=[c.Slack for c in lcons])
    return rec


def mip_record(inst, args):
    m, vs, cs = build_model(inst, args.threads, args.seed, verbose=args.verbose)
    m.Params.MIPGap = args.mip_gap
    m.Params.MIPGapAbs = args.mip_gap_abs
    if args.time_limit is not None:
        m.Params.TimeLimit = args.time_limit
    m._vs, m._inc = vs, []
    integral = [v.VType != GRB.CONTINUOUS for v in vs]

    def cb(model, where):
        if where == GRB.Callback.MIPSOL:
            x = model.cbGetSolution(model._vs)
            model._inc.append({
                "time_s": model.cbGet(GRB.Callback.RUNTIME),
                "objective": model.cbGet(GRB.Callback.MIPSOL_OBJ),
                "nodes": int(model.cbGet(GRB.Callback.MIPSOL_NODCNT)),
                "x": [round(a) if i else a for a, i in zip(x, integral)],
            })

    m.optimize(cb)
    rec = {"status": _status(m.Status), "time_s": m.Runtime, "nodes": int(m.NodeCount),
           "time_limit_hit": m.Status == GRB.TIME_LIMIT, "n_solutions": m.SolCount,
           "objective": None, "best_bound": None, "gap": None, "solution": None}
    if m.SolCount > 0:
        rec.update(objective=m.ObjVal, gap=m.MIPGap,
                   solution=[round(v.X) if i else v.X for v, i in zip(vs, integral)])
    if m.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL):
        rec["best_bound"] = m.ObjBound
    rec["incumbents"] = m._inc
    return rec


STATUS_NAMES = {GRB.LOADED: "LOADED", GRB.OPTIMAL: "OPTIMAL", GRB.INFEASIBLE: "INFEASIBLE",
                GRB.INF_OR_UNBD: "INF_OR_UNBD", GRB.UNBOUNDED: "UNBOUNDED", GRB.CUTOFF: "CUTOFF",
                GRB.ITERATION_LIMIT: "ITERATION_LIMIT", GRB.NODE_LIMIT: "NODE_LIMIT",
                GRB.TIME_LIMIT: "TIME_LIMIT", GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
                GRB.INTERRUPTED: "INTERRUPTED", GRB.NUMERIC: "NUMERIC", GRB.SUBOPTIMAL: "SUBOPTIMAL"}


def _status(code):
    return STATUS_NAMES.get(code, str(code))


def make_label(path, args):
    raw = Path(path).read_bytes()
    inst = json.loads(raw)
    label = {
        "instance_id": inst["id"],
        "instance_sha256": hashlib.sha256(raw).hexdigest(),
        "family": inst["family"],
        "sense": inst["sense"],
        "gurobi": {"version": ".".join(map(str, gp.gurobi.version())), "threads": args.threads,
                   "seed": args.seed, "time_limit_s": args.time_limit,
                   "mip_gap": args.mip_gap, "mip_gap_abs": args.mip_gap_abs},
        "variables": [v["name"] for v in inst["variables"]],
        "constraints": [c["name"] for c in inst["constraints"]],
        "lp_relaxation": lp_record(inst, args),
        "mip": mip_record(inst, args),
    }
    bk = inst.get("meta", {}).get("best_known")
    if bk is not None:
        label["best_known"] = bk
    return label


def check_best_known(label):
    """Return (text, ok) comparing the MIP objective with meta.best_known."""
    bk, obj = label.get("best_known"), label["mip"]["objective"]
    if bk is None:
        return "", True
    if obj is None:
        return "best_known=%g, no solution found" % bk, True
    sign = 1 if label["sense"] == "max" else -1
    diff = sign * (obj - bk)
    optimal = label["mip"]["status"] == "OPTIMAL"
    if abs(diff) < 0.5 + 1e-6 * abs(bk):
        return "= best_known %g" % bk, True
    if diff > 0:
        return "BETTER than best_known %g (+%g)" % (bk, diff), True
    return "below best_known %g (%g)%s" % (bk, diff, " -- OPTIMAL but below!" if optimal else ""), not optimal


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
    ap.add_argument("--time-limit", type=float, default=None, help="MIP time limit in seconds (the final gap is saved)")
    ap.add_argument("--mip-gap", type=float, default=0.0, help="relative MIP gap (default 0: prove optimality)")
    ap.add_argument("--mip-gap-abs", type=float, default=1e-6)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="show the Gurobi MIP log")
    args = ap.parse_args(argv)

    files = collect(args.paths)
    if not files:
        sys.exit("no instance files found")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    print(f"{'instance':44} {'LP obj':>12} {'MIP obj':>12} {'status':>10} {'gap':>9} {'time[s]':>8} {'#inc':>5}")
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
        lp, mip = label["lp_relaxation"], label["mip"]
        fmt = lambda x: "-" if x is None else f"{x:.6g}"
        note, ok = check_best_known(label)
        failed += not ok
        gap = "-" if mip["gap"] is None else f"{mip['gap']:.2%}"
        print(f"{label['instance_id']:44} {fmt(lp.get('objective')):>12} {fmt(mip['objective']):>12} "
              f"{mip['status']:>10} {gap:>9} {mip['time_s']:8.3f} {len(mip['incumbents']):5d}  {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
