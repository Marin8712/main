import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import generate as g

SCRIPT = Path(__file__).resolve().parent / "generate.py"
VAR_TYPES = {"real", "integer", "binary"}


def run_cli(*args, hashseed="0"):
    env = dict(os.environ, PYTHONHASHSEED=hashseed)
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], check=True,
                          capture_output=True, env=env).stdout


class Determinism(unittest.TestCase):
    def test_same_seed_same_bytes_in_process(self):
        for t in g.TYPES:
            a = g.dumps(g.generate(t, 200, seed=42))
            b = g.dumps(g.generate(t, 200, seed=42))
            self.assertEqual(a, b, t)

    def test_same_seed_same_bytes_across_processes(self):
        for t, extra in [("uncorrelated", []), ("weak", []), ("strong", []),
                         ("chu-beasley", ["--m", "5"])]:
            args = ["--type", t, "--n", "100", "--seed", "42", *extra]
            self.assertEqual(run_cli(*args, hashseed="1"), run_cli(*args, hashseed="999"), t)

    def test_files_identical_on_disk(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = Path(d, "a.json"), Path(d, "b.json")
            run_cli("--type", "weak", "--n", "50", "--seed", "42", "--out", str(p1))
            run_cli("--type", "weak", "--n", "50", "--seed", "42", "--out", str(p2))
            self.assertEqual(p1.read_bytes(), p2.read_bytes())

    def test_different_seed_differs(self):
        self.assertNotEqual(g.dumps(g.generate("weak", 50, seed=1)),
                            g.dumps(g.generate("weak", 50, seed=2)))

    def test_output_is_valid_json(self):
        inst = json.loads(g.dumps(g.generate("chu-beasley", 20, m=3, seed=3)))
        self.assertEqual(inst, g.generate("chu-beasley", 20, m=3, seed=3))


class Single(unittest.TestCase):
    R = 1000

    def parts(self, t, n=500, seed=5):
        inst = g.generate(t, n, seed=seed)
        p = [v["objective"] for v in inst["variables"]]
        c = inst["constraints"][0]
        w = [c["terms"][v["name"]] for v in inst["variables"]]
        return inst, p, w, c

    def test_schema(self):
        inst, *_ = self.parts("uncorrelated", 10)
        self.assertEqual(inst["family"], "knapsack")
        self.assertEqual(inst["sense"], "max")
        self.assertTrue(all(v["type"] in VAR_TYPES for v in inst["variables"]))
        self.assertEqual(inst["constraints"][0]["name"], "capacity")
        self.assertEqual(inst["constraints"][0]["op"], "<=")

    def test_uncorrelated(self):
        _, p, w, _ = self.parts("uncorrelated")
        self.assertTrue(all(1 <= x <= self.R for x in p + w))

    def test_weak(self):
        _, p, w, _ = self.parts("weak")
        self.assertTrue(all(1 <= x <= self.R for x in w))
        self.assertTrue(all(p_ >= 1 and abs(p_ - w_) <= self.R // 10 for p_, w_ in zip(p, w)))
        self.assertTrue(any(p_ != w_ for p_, w_ in zip(p, w)))

    def test_strong(self):
        _, p, w, _ = self.parts("strong")
        self.assertTrue(all(p_ == w_ + self.R // 10 for p_, w_ in zip(p, w)))

    def test_capacity(self):
        _, _, w, c = self.parts("strong")
        self.assertEqual(c["rhs"], int(0.5 * sum(w)))

    def test_m_gt_1_rejected_for_single_types(self):
        with self.assertRaises(ValueError):
            g.generate("weak", 10, m=2)


class ChuBeasley(unittest.TestCase):
    def test_structure(self):
        n, m, alpha = 100, 5, 0.25
        inst = g.generate("chu-beasley", n, m=m, seed=11, tightness=alpha)
        self.assertEqual(len(inst["constraints"]), m)
        self.assertEqual([c["name"] for c in inst["constraints"]], [f"capacity{i}" for i in range(1, m + 1)])
        names = [v["name"] for v in inst["variables"]]
        a = [[c["terms"].get(x, 0) for x in names] for c in inst["constraints"]]
        for row, c in zip(a, inst["constraints"]):
            self.assertTrue(all(0 <= x <= 1000 for x in row))
            self.assertEqual(c["rhs"], int(alpha * sum(row)))
        for j, v in enumerate(inst["variables"]):
            base = sum(a[i][j] for i in range(m)) / m
            self.assertTrue(base - 1 <= v["objective"] <= base + 501, (j, v))

    def test_m_argument_on_cli(self):
        inst = json.loads(run_cli("--type", "chu-beasley", "--n", "30", "--m", "10", "--seed", "1"))
        self.assertEqual(len(inst["constraints"]), 10)
        self.assertEqual(inst["meta"]["m"], 10)


if __name__ == "__main__":
    unittest.main()
