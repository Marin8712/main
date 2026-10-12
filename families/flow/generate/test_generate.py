import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import generate as g

SCRIPT = Path(__file__).resolve().parent / "generate.py"
VAR_TYPES = {"real", "integer", "binary"}


def run_cli(*args, hashseed="0"):
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], check=True,
                          capture_output=True, env=env).stdout


def rhs_of(inst):
    return [c["rhs"] for c in inst["constraints"] if c["name"].startswith("node_")]


class Determinism(unittest.TestCase):
    def test_same_seed_same_bytes_in_process(self):
        for t in g.TYPES:
            a = g.dumps(g.generate(t, 40, seed=42))
            b = g.dumps(g.generate(t, 40, seed=42))
            self.assertEqual(a, b, t)

    def test_same_seed_same_bytes_across_processes(self):
        for t in g.TYPES:
            args = ["--type", t, "--n", "30", "--seed", "42"]
            self.assertEqual(run_cli(*args, hashseed="1"), run_cli(*args, hashseed="999"), t)

    def test_files_identical_on_disk(self):
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = Path(d, "a.json"), Path(d, "b.json")
            run_cli("--type", "mcf", "--n", "50", "--m", "200", "--seed", "42", "--out", str(p1))
            run_cli("--type", "mcf", "--n", "50", "--m", "200", "--seed", "42", "--out", str(p2))
            self.assertEqual(p1.read_bytes(), p2.read_bytes())

    def test_different_seed_differs(self):
        for t in g.TYPES:
            self.assertNotEqual(g.dumps(g.generate(t, 20, seed=1)), g.dumps(g.generate(t, 20, seed=2)), t)

    def test_output_is_valid_json(self):
        inst = g.generate("mcf", 20, m=60, seed=3)
        self.assertEqual(json.loads(g.dumps(inst)), inst)


class Structure(unittest.TestCase):
    def test_schema(self):
        for t in g.TYPES:
            inst = g.generate(t, 12, seed=5)
            self.assertEqual(inst["family"], "flow")
            self.assertEqual(inst["sense"], "min")
            self.assertTrue(all(v["type"] in VAR_TYPES for v in inst["variables"]))
            self.assertEqual(len({v["name"] for v in inst["variables"]}), len(inst["variables"]))
            self.assertEqual(len({c["name"] for c in inst["constraints"]}), len(inst["constraints"]))
            self.assertEqual(sum(rhs_of(inst)), 0, t)
            self.assertEqual(len(rhs_of(inst)), 12)

    def test_each_arc_in_two_node_rows(self):
        inst = g.generate("mcf", 15, m=50, seed=2)
        count = {}
        for c in inst["constraints"]:
            if c["name"].startswith("node_"):
                for var, coef in c["terms"].items():
                    count.setdefault(var, []).append(coef)
        self.assertEqual(len(count), 50)
        self.assertTrue(all(sorted(v) == [-1, 1] for v in count.values()))

    def test_mcf_backbone_and_arc_count(self):
        n, m = 20, 70
        inst = g.generate("mcf", n, m=m, seed=7)
        self.assertEqual(len(inst["variables"]), m)
        names = {v["name"] for v in inst["variables"]}
        self.assertTrue(all(f"x_{i}_{i % n + 1}" in names for i in range(1, n + 1)))
        total = inst["meta"]["supply_total"]
        self.assertEqual(sum(r for r in rhs_of(inst) if r > 0), total)

    def test_transportation_is_bipartite_without_capacities(self):
        inst = g.generate("transportation", 11, seed=4)
        s, t = inst["meta"]["sources"], inst["meta"]["sinks"]
        self.assertEqual((s, t), (5, 6))
        self.assertEqual(len(inst["variables"]), s * t)
        self.assertFalse(any(c["name"].startswith("cap_") for c in inst["constraints"]))
        rhs = rhs_of(inst)
        self.assertTrue(all(r > 0 for r in rhs[:s]) and all(r < 0 for r in rhs[s:]))
        for v in inst["variables"]:
            _, i, j = v["name"].split("_")
            self.assertTrue(int(i) <= s < int(j))

    def test_shortest_path_unit_supply_no_capacities(self):
        inst = g.generate("shortest-path", 15, seed=4)
        rhs = rhs_of(inst)
        self.assertEqual((rhs[0], rhs[-1], sum(abs(r) for r in rhs)), (1, -1, 2))
        self.assertFalse(any(c["name"].startswith("cap_") for c in inst["constraints"]))
        self.assertTrue(all(v["objective"] >= 1 for v in inst["variables"]))

    def test_max_flow_return_arc(self):
        n = 15
        inst = g.generate("max-flow", n, seed=4)
        ret = [v for v in inst["variables"] if v["objective"] != 0]
        self.assertEqual(ret, [{"name": f"x_{n}_1", "type": "real", "objective": -1}])
        self.assertFalse(any(c["name"] == f"cap_{n}_1" for c in inst["constraints"]))
        self.assertEqual(rhs_of(inst), [0] * n)
        self.assertEqual(inst["meta"]["objective_sign"], -1)
        self.assertEqual(len(inst["variables"]), inst["meta"]["m"])

    def test_dense_request_uses_full_graph(self):
        inst = g.generate("mcf", 6, m=30, seed=1)          # all n(n-1) arcs
        self.assertEqual(len({v["name"] for v in inst["variables"]}), 30)

    def test_bad_arguments(self):
        with self.assertRaises(ValueError):
            g.generate("transportation", 10, m=5)
        with self.assertRaises(ValueError):
            g.generate("mcf", 10, m=5)
        with self.assertRaises(ValueError):
            g.generate("mcf", 5, m=21)
        with self.assertRaises(ValueError):
            g.generate("bogus", 5)


if __name__ == "__main__":
    unittest.main()
