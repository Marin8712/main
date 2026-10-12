import heapq
import importlib.util
import tempfile
import unittest
from argparse import Namespace
from collections import deque
from pathlib import Path

import gurobipy as gp

import make_labels as ml

_spec = importlib.util.spec_from_file_location(
    "generate", Path(__file__).resolve().parent.parent / "generate" / "generate.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

ARGS = dict(threads=1, seed=0, time_limit=None, method=1, verbose=False)


def label_of(inst, **over):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d, "i.json")
        p.write_text(gen.dumps(inst))
        return ml.make_label(p, Namespace(**{**ARGS, **over}))


def parse(inst):
    """arcs {(i, j): (cost, cap_or_None)} and supplies {node: b} from an instance."""
    caps = {}
    for c in inst["constraints"]:
        if c["name"].startswith("cap_"):
            (var,) = c["terms"]
            caps[var] = c["rhs"]
    arcs = {}
    for v in inst["variables"]:
        _, i, j = v["name"].split("_")
        arcs[(int(i), int(j))] = (v["objective"], caps.get(v["name"]))
    b = {int(c["name"].split("_")[1]): c["rhs"] for c in inst["constraints"] if c["name"].startswith("node_")}
    return arcs, b


def dijkstra(arcs, s, t):
    adj = {}
    for (i, j), (c, _) in arcs.items():
        adj.setdefault(i, []).append((j, c))
    dist, heap = {s: 0}, [(0, s)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == t:
            return d
        if d > dist.get(u, float("inf")):
            continue
        for v, c in adj.get(u, []):
            if d + c < dist.get(v, float("inf")):
                dist[v] = d + c
                heapq.heappush(heap, (d + c, v))
    return None


def edmonds_karp(cap, s, t):
    """cap: {(i, j): capacity}; returns max flow value."""
    res = dict(cap)
    for (i, j) in list(cap):
        res.setdefault((j, i), 0)
    adj = {}
    for (i, j) in res:
        adj.setdefault(i, []).append(j)
    flow = 0
    while True:
        parent, q = {s: None}, deque([s])
        while q and t not in parent:
            u = q.popleft()
            for v in adj.get(u, []):
                if v not in parent and res[(u, v)] > 0:
                    parent[v] = u
                    q.append(v)
        if t not in parent:
            return flow
        path, v = [], t
        while parent[v] is not None:
            path.append((parent[v], v))
            v = parent[v]
        push = min(res[e] for e in path)
        for (u, v) in path:
            res[(u, v)] -= push
            res[(v, u)] += push
        flow += push


def direct_mcf(arcs, b):
    """Independent model: capacities as variable bounds, conservation rows built from arrays."""
    m = gp.Model()
    m.Params.OutputFlag = 0
    keys = list(arcs)
    x = m.addVars(keys, lb=0, ub={k: (arcs[k][1] if arcs[k][1] is not None else gp.GRB.INFINITY) for k in keys},
                  obj={k: arcs[k][0] for k in keys})
    for v, supply in b.items():
        m.addConstr(gp.quicksum(x[k] for k in keys if k[0] == v) - gp.quicksum(x[k] for k in keys if k[1] == v) == supply)
    m.optimize()
    assert m.Status == gp.GRB.OPTIMAL
    return m.ObjVal


class Reductions(unittest.TestCase):
    def test_shortest_path_equals_dijkstra(self):
        for seed in range(5):
            inst = gen.generate("shortest-path", 40, m=160, seed=seed)
            arcs, _ = parse(inst)
            lab = label_of(inst)
            self.assertEqual(lab["lp_relaxation"]["status"], "OPTIMAL")
            self.assertAlmostEqual(lab["original_objective"], dijkstra(arcs, 1, 40), places=6, msg=seed)

    def test_max_flow_equals_edmonds_karp(self):
        for seed in range(5):
            inst = gen.generate("max-flow", 30, m=120, seed=seed)
            arcs, _ = parse(inst)
            cap = {k: v[1] for k, v in arcs.items() if v[1] is not None}
            lab = label_of(inst)
            self.assertAlmostEqual(lab["original_objective"], edmonds_karp(cap, 1, 30), places=6, msg=seed)
            self.assertAlmostEqual(lab["original_objective"], -lab["lp_relaxation"]["objective"])

    def test_transportation_equals_direct_lp(self):
        for seed in range(4):
            inst = gen.generate("transportation", 14, seed=seed)
            arcs, b = parse(inst)
            s = inst["meta"]["sources"]
            m = gp.Model()
            m.Params.OutputFlag = 0
            x = m.addVars(list(arcs), lb=0, obj={k: arcs[k][0] for k in arcs})
            for i in range(1, s + 1):
                m.addConstr(x.sum(i, "*") == b[i])
            for j in range(s + 1, 15):
                m.addConstr(x.sum("*", j) == -b[j])
            m.optimize()
            self.assertAlmostEqual(label_of(inst)["lp_relaxation"]["objective"], m.ObjVal, places=6)

    def test_mcf_equals_direct_bounds_model(self):
        for seed in range(5):
            inst = gen.generate("mcf", 30, m=120, seed=seed)
            arcs, b = parse(inst)
            self.assertAlmostEqual(label_of(inst)["lp_relaxation"]["objective"], direct_mcf(arcs, b), places=5, msg=seed)


class LabelContent(unittest.TestCase):
    def setUp(self):
        self.inst = gen.generate("mcf", 40, m=160, seed=3)
        self.lab = label_of(self.inst)
        self.lp = self.lab["lp_relaxation"]

    def test_layout(self):
        self.assertEqual(self.lab["mip"], None)
        self.assertEqual(len(self.lab["variables"]), 160)
        self.assertEqual(len(self.lp["x"]), 160)
        self.assertEqual(len(self.lp["reduced_costs"]), 160)
        self.assertEqual(len(self.lp["duals"]), len(self.inst["constraints"]))
        self.assertEqual(self.lab["constraints"][:3], ["node_1", "node_2", "node_3"])
        self.assertGreater(self.lp["iterations"], 0)

    def test_solution_feasible_and_integral(self):
        arcs, b = parse(self.inst)
        x = dict(zip(self.lab["variables"], self.lp["x"]))
        net = {v: 0.0 for v in b}
        for (i, j), (c, cap) in arcs.items():
            f = x[f"x_{i}_{j}"]
            self.assertGreaterEqual(f, -1e-9)
            if cap is not None:
                self.assertLessEqual(f, cap + 1e-9)
            self.assertAlmostEqual(f, round(f), places=6)       # total unimodularity
            net[i] += f
            net[j] -= f
        for v in b:
            self.assertAlmostEqual(net[v], b[v], places=6)
        self.assertAlmostEqual(sum(c * x[f"x_{i}_{j}"] for (i, j), (c, _) in arcs.items()), self.lp["objective"], places=5)

    def test_strong_duality_and_signs(self):
        duals = dict(zip(self.lab["constraints"], self.lp["duals"]))
        dual_obj = sum(duals[c["name"]] * c["rhs"] for c in self.inst["constraints"])
        self.assertAlmostEqual(dual_obj, self.lp["objective"], places=5)
        self.assertTrue(all(d <= 1e-9 for name, d in duals.items() if name.startswith("cap_")))

    def test_reduced_cost_identity(self):
        # reduced cost of arc (i,j) = c_ij - Pi_i + Pi_j - Pi_cap_ij (cap row only if capacitated)
        duals = dict(zip(self.lab["constraints"], self.lp["duals"]))
        for var, c, rc in zip(self.inst["variables"], [v["objective"] for v in self.inst["variables"]],
                              self.lp["reduced_costs"]):
            _, i, j = var["name"].split("_")
            expect = c - duals[f"node_{i}"] + duals[f"node_{j}"] - duals.get(f"cap_{i}_{j}", 0.0)
            self.assertAlmostEqual(rc, expect, places=5, msg=var["name"])

    def test_methods_agree(self):
        objs = {m: label_of(self.inst, method=m)["lp_relaxation"]["objective"] for m in (0, 1, 2)}
        self.assertAlmostEqual(objs[0], objs[1], places=5)
        self.assertAlmostEqual(objs[1], objs[2], places=3)

    def test_time_limit_is_recorded(self):
        lab = label_of(self.inst, time_limit=0.0)
        lp = lab["lp_relaxation"]
        self.assertIn(lp["status"], ("OPTIMAL", "TIME_LIMIT"))
        if lp["status"] == "TIME_LIMIT":
            self.assertTrue(lp["time_limit_hit"])
            self.assertIsNone(lp["x"])

    def test_non_real_variable_rejected(self):
        bad = gen.generate("mcf", 10, seed=1)
        bad["variables"][0]["type"] = "binary"
        with self.assertRaises(ValueError):
            label_of(bad)


class BestKnown(unittest.TestCase):
    def test_check(self):
        base = {"original_objective": 100.0}
        self.assertTrue(ml.check_best_known({**base, "best_known": 100})[1])
        self.assertFalse(ml.check_best_known({**base, "best_known": 99})[1])
        self.assertTrue(ml.check_best_known(base)[1])
        self.assertTrue(ml.check_best_known({"original_objective": None, "best_known": 5})[1])


if __name__ == "__main__":
    unittest.main()
