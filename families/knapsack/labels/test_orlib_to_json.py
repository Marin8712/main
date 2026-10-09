import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
def load(name, rel):
    s = importlib.util.spec_from_file_location(name, HERE / rel)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

o2j = load("orlib_to_json", "orlib_to_json.py")
gen = load("generate", "../generate/generate.py")


def to_orlib(insts, best=0):
    """Write generated MKP instances in OR-Library text format."""
    lines = [str(len(insts))]
    for inst in insts:
        names = [v["name"] for v in inst["variables"]]
        n, m = len(names), len(inst["constraints"])
        lines.append(f" {n} {m} {best}")
        lines.append(" ".join(str(v["objective"]) for v in inst["variables"]))
        for c in inst["constraints"]:
            lines.append(" ".join(str(c["terms"].get(x, 0)) for x in names))
        lines.append(" ".join(str(c["rhs"]) for c in inst["constraints"]))
    return "\n".join(lines) + "\n"


class OrlibRoundTrip(unittest.TestCase):
    def test_round_trip(self):
        src = [gen.generate("chu-beasley", 25, m=4, seed=s) for s in (1, 2)]
        out = list(o2j.parse(to_orlib(src), "mknapcbX"))
        self.assertEqual([i["id"] for i in out], ["orlib-mknapcbX-01", "orlib-mknapcbX-02"])
        for a, b in zip(src, out):
            self.assertEqual(a["variables"], b["variables"])
            self.assertEqual(a["constraints"], b["constraints"])
            self.assertNotIn("best_known", b["meta"])

    def test_header_best_known(self):
        out = list(o2j.parse(to_orlib([gen.generate("chu-beasley", 5, m=2, seed=1)], best=1234), "f"))
        self.assertEqual(out[0]["meta"]["best_known"], 1234)

    def test_truncated_file_rejected(self):
        with self.assertRaises(ValueError):
            list(o2j.parse(to_orlib([gen.generate("chu-beasley", 5, m=2, seed=1)])[:-6], "f"))

    def test_cli_with_best_known_csv(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "mknapcbX.txt").write_text(to_orlib([gen.generate("chu-beasley", 6, m=2, seed=1)]))
            (d / "bk.csv").write_text("orlib-mknapcbX-01,777\n")
            o2j.main([str(d / "mknapcbX.txt"), "--out-dir", str(d / "o"), "--best-known", str(d / "bk.csv")])
            inst = json.loads((d / "o" / "orlib-mknapcbX-01.json").read_text())
            self.assertEqual(inst["meta"]["best_known"], 777)


if __name__ == "__main__":
    unittest.main()
