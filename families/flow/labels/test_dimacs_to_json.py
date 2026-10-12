import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, rel):
    s = importlib.util.spec_from_file_location(name, HERE / rel)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


d2j = load("dimacs_to_json", "dimacs_to_json.py")
gen = load("generate", "../generate/generate.py")


def to_dimacs_min(inst):
    n = inst["meta"]["n"]
    arcs = {}
    for c in inst["constraints"]:
        if c["name"].startswith("cap_"):
            (var,) = c["terms"]
            arcs[var] = c["rhs"]
    lines = [f"c generated", f"p min {n} {len(inst['variables'])}"]
    for c in inst["constraints"]:
        if c["name"].startswith("node_") and c["rhs"] != 0:
            lines.append(f"n {c['name'][5:]} {c['rhs']}")
    for v in inst["variables"]:
        _, i, j = v["name"].split("_")
        lines.append(f"a {i} {j} 0 {arcs[v['name']]} {v['objective']}")
    return "\n".join(lines) + "\n"


def to_dimacs_max(inst):
    n = inst["meta"]["n"]
    caps = {}
    for c in inst["constraints"]:
        if c["name"].startswith("cap_"):
            (var,) = c["terms"]
            caps[var] = c["rhs"]
    arcs = [v["name"] for v in inst["variables"] if v["name"] in caps]
    lines = [f"p max {n} {len(arcs)}", "n 1 s", f"n {n} t"]
    lines += [f"a {nm.split('_')[1]} {nm.split('_')[2]} {caps[nm]}" for nm in arcs]
    return "\n".join(lines) + "\n"


class RoundTrip(unittest.TestCase):
    def test_min_round_trip_matches_generator(self):
        src = gen.generate("mcf", 25, m=90, seed=3)
        out = d2j.parse(to_dimacs_min(src), "net1")
        self.assertEqual(out["id"], "dimacs-net1")
        self.assertEqual(out["variables"], src["variables"])
        self.assertEqual(out["constraints"], src["constraints"])
        self.assertEqual(out["sense"], "min")

    def test_max_round_trip_matches_generator(self):
        src = gen.generate("max-flow", 20, m=70, seed=2)
        out = d2j.parse(to_dimacs_max(src), "mf1")
        self.assertEqual(out["variables"], src["variables"])
        self.assertEqual(out["constraints"], src["constraints"])
        self.assertEqual(out["meta"]["objective_sign"], -1)

    def test_parallel_arcs_get_unique_names(self):
        text = "p min 2 2\nn 1 3\nn 2 -3\na 1 2 0 5 1\na 1 2 0 5 2\n"
        inst = d2j.parse(text, "par")
        self.assertEqual([v["name"] for v in inst["variables"]], ["x_1_2", "x_1_2_2"])
        self.assertEqual([c["name"] for c in inst["constraints"] if c["name"].startswith("cap_")],
                         ["cap_1_2", "cap_1_2_2"])

    def test_lower_bound_row(self):
        inst = d2j.parse("p min 2 1\nn 1 3\nn 2 -3\na 1 2 2 9 1\n", "lo")
        low = [c for c in inst["constraints"] if c["name"].startswith("low_")]
        self.assertEqual(low, [{"name": "low_1_2", "terms": {"x_1_2": 1}, "op": ">=", "rhs": 2}])

    def test_errors(self):
        for text in ["a 1 2 0 5 1\n",                                   # no p line
                     "p min 2 1\nn 1 3\na 1 2 0 5 1\n",                  # supplies unbalanced
                     "p min 2 2\nn 1 0\na 1 2 0 5 1\n",                  # arc count mismatch
                     "p sp 2 1\na 1 2 3\n",                              # unsupported
                     "p max 2 1\na 1 2 3\n",                             # no s/t
                     "p min 2 1\nn 1 0\na 1 2 0 5\n"]:                   # short arc line
            with self.assertRaises(ValueError, msg=text):
                d2j.parse(text, "bad")

    def test_cli_with_best_known(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = gen.generate("max-flow", 10, m=30, seed=1)
            (d / "mf1.max").write_text(to_dimacs_max(src))
            (d / "bk.csv").write_text("dimacs-mf1,42\n")
            d2j.main([str(d / "mf1.max"), "--out-dir", str(d / "o"), "--best-known", str(d / "bk.csv")])
            inst = json.loads((d / "o" / "dimacs-mf1.json").read_text())
            self.assertEqual(inst["meta"]["best_known"], 42)


if __name__ == "__main__":
    unittest.main()
