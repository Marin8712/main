import importlib.util
import itertools
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import make_labels as ml

_spec = importlib.util.spec_from_file_location(
    "generate", Path(__file__).resolve().parent.parent / "generate" / "generate.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

ARGS = dict(threads=1, seed=0, time_limit=None, mip_gap=0.0, mip_gap_abs=1e-6, verbose=False)


def label_of(inst, **over):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d, "i.json")
        p.write_text(gen.dumps(inst))
        return ml.make_label(p, Namespace(**{**ARGS, **over}))


def dp_opt(inst):
    p = [v["objective"] for v in inst["variables"]]
    t = inst["constraints"][0]["terms"]
    w = [t[v["name"]] for v in inst["variables"]]
    best = [0] * (inst["constraints"][0]["rhs"] + 1)
    for pj, wj in zip(p, w):
        for c in range(len(best) - 1, wj - 1, -1):
            best[c] = max(best[c], best[c - wj] + pj)
    return best[-1]


def brute_opt(inst):
    names = [v["name"] for v in inst["variables"]]
    p = [v["objective"] for v in inst["variables"]]
    best = 0
    for x in itertools.product((0, 1), repeat=len(names)):
        if all(sum(c["terms"].get(n, 0) * xi for n, xi in zip(names, x)) <= c["rhs"]
               for c in inst["constraints"]):
            best = max(best, sum(a * b for a, b in zip(p, x)))
    return best


class Knapsack01(unittest.TestCase):
    def test_optimum_matches_dp(self):
        for t in ("uncorrelated", "weak", "strong"):
            for seed in range(3):
                inst = gen.generate(t, 60, seed=seed, rng_range=100)
                lab = label_of(inst)
                self.assertEqual(lab["mip"]["status"], "OPTIMAL")
                self.assertAlmostEqual(lab["mip"]["objective"], dp_opt(inst), places=4, msg=(t, seed))

    def test_solution_feasible_and_consistent(self):
        inst = gen.generate("weak", 80, seed=4)
        lab = label_of(inst)
        x = lab["mip"]["solution"]
        w = [inst["constraints"][0]["terms"][v["name"]] for v in inst["variables"]]
        self.assertLessEqual(sum(a * b for a, b in zip(w, x)), inst["constraints"][0]["rhs"])
        self.assertEqual(sum(v["objective"] * xi for v, xi in zip(inst["variables"], x)),
                         round(lab["mip"]["objective"]))
        self.assertEqual(len(lab["variables"]), 80)
        self.assertEqual(len(lab["lp_relaxation"]["reduced_costs"]), 80)

    def test_incumbents_improve_and_end_at_optimum(self):
        lab = label_of(gen.generate("strong", 150, seed=2))
        inc = lab["mip"]["incumbents"]
        self.assertTrue(inc)
        objs = [i["objective"] for i in inc]
        times = [i["time_s"] for i in inc]
        self.assertEqual(objs, sorted(objs))
        self.assertEqual(times, sorted(times))
        self.assertAlmostEqual(objs[-1], lab["mip"]["objective"])
        self.assertEqual(inc[-1]["x"], lab["mip"]["solution"])

    def test_lp_bound_and_strong_duality(self):
        inst = gen.generate("weak", 100, seed=9)
        lab = label_of(inst)
        lp = lab["lp_relaxation"]
        self.assertGreaterEqual(lp["objective"], lab["mip"]["objective"] - 1e-6)
        dual = sum(pi * c["rhs"] for pi, c in zip(lp["duals"], inst["constraints"]))
        dual += sum(max(rc, 0.0) for rc in lp["reduced_costs"])   # ub = 1 on binaries
        self.assertAlmostEqual(dual, lp["objective"], places=5)
        self.assertTrue(all(pi >= -1e-9 for pi in lp["duals"]))   # max, <= rows


class MKP(unittest.TestCase):
    def test_small_mkp_matches_brute_force(self):
        for seed in range(4):
            for m in (2, 3, 5):
                inst = gen.generate("chu-beasley", 14, m=m, seed=seed)
                lab = label_of(inst)
                self.assertEqual(lab["mip"]["status"], "OPTIMAL")
                self.assertAlmostEqual(lab["mip"]["objective"], brute_opt(inst), places=4, msg=(seed, m))

    def test_one_dual_per_capacity_constraint(self):
        inst = gen.generate("chu-beasley", 60, m=7, seed=3)
        lab = label_of(inst)
        lp = lab["lp_relaxation"]
        self.assertEqual(lab["constraints"], [f"capacity{i}" for i in range(1, 8)])
        self.assertEqual(len(lp["duals"]), 7)
        dual = sum(pi * c["rhs"] for pi, c in zip(lp["duals"], inst["constraints"]))
        dual += sum(max(rc, 0.0) for rc in lp["reduced_costs"])
        self.assertAlmostEqual(dual, lp["objective"], places=4)
        self.assertTrue(all(pi >= -1e-9 for pi in lp["duals"]))

    def test_time_limit_saves_gap(self):
        inst = gen.generate("chu-beasley", 500, m=30, seed=1, tightness=0.25)
        lab = label_of(inst, time_limit=1.0)
        mip = lab["mip"]
        self.assertEqual(mip["status"], "TIME_LIMIT")
        self.assertTrue(mip["time_limit_hit"])
        self.assertGreater(mip["gap"], 0)
        self.assertLessEqual(mip["objective"], mip["best_bound"] + 1e-6)
        self.assertLess(mip["time_s"], 5.0)
        self.assertGreater(len(mip["incumbents"]), 0)


class BestKnown(unittest.TestCase):
    def test_check(self):
        base = {"sense": "max", "mip": {"objective": 100.0, "status": "OPTIMAL"}}
        self.assertTrue(ml.check_best_known({**base, "best_known": 100})[1])
        self.assertTrue(ml.check_best_known({**base, "best_known": 90})[1])
        self.assertFalse(ml.check_best_known({**base, "best_known": 110})[1])
        tl = {"sense": "max", "mip": {"objective": 100.0, "status": "TIME_LIMIT"}, "best_known": 110}
        self.assertTrue(ml.check_best_known(tl)[1])


if __name__ == "__main__":
    unittest.main()
