#!/usr/bin/env python3
"""Checks for the site generator. Run with python3 -I tools/site/test_sitegen.py."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sitegen

ROOT = pathlib.Path(__file__).resolve().parents[2]

EVIDENCE = """### conformance/ops/a.st
0 => x=1
PASS    conformance/ops/a.st
### conformance/ops/b.st
FAIL    conformance/ops/b.st
        cycle 0 (trace line 9): x expected 1, got 2

### conformance/undefined/c.st
SAME    conformance/undefined/c.st (implementation-defined)

3 tests: 1 pass, 1 fail, 1 same, 0 differs, 0 error
exit 1
"""


class Parsing(unittest.TestCase):
    def test_evidence_blocks_and_verdicts(self):
        ev = sitegen.parse_evidence(EVIDENCE)
        self.assertEqual(sorted(ev), ["conformance/ops/a.st", "conformance/ops/b.st", "conformance/undefined/c.st"])
        self.assertEqual(ev["conformance/ops/a.st"]["verdict"], "PASS")
        self.assertEqual(ev["conformance/ops/b.st"]["verdict"], "FAIL")
        self.assertEqual(ev["conformance/undefined/c.st"]["verdict"], "SAME")
        self.assertIn("x expected 1, got 2", ev["conformance/ops/b.st"]["text"])
        self.assertNotIn("3 tests:", ev["conformance/undefined/c.st"]["text"])

    def test_totals_line(self):
        md = "Totals (109 tests, 91 with `status: conformant`): conformant tests passed, IronPLC 64/91; matiec 80/91; rk 64/91. 19 of the 109 tests"
        t = sitegen.parse_totals(md)
        self.assertEqual(t["tests"], 109)
        self.assertEqual(t["conformant"], 91)
        self.assertEqual(t["passed"]["matiec"], 80)
        self.assertEqual(t["passed"]["IronPLC"], 64)

    def test_results_table_between_markers(self):
        md = "intro\n<!-- results:begin -->\n| a | b |\n|---|---|\n<!-- results:end -->\nrest"
        self.assertEqual(sitegen.between_markers(md).strip(), "| a | b |\n|---|---|")

    def test_pins_from_ci(self):
        ci = "env:\n  IRONPLC_SHA: 6e40df279fc208fc1f3ee6efa11db7a4d9c10c65\n  FOURDIAC_VERSION: \"3.3.0\"   # comment\n"
        self.assertEqual(sitegen.parse_pins(ci), {"IRONPLC_SHA": "6e40df279fc208fc1f3ee6efa11db7a4d9c10c65", "FOURDIAC_VERSION": "3.3.0"})

    def test_upstream_references(self):
        text = ("see beremiz/matiec#54, ironplc#2615 and https://github.com/PLC-lang/rusty/issues/2035; "
                "STruCpp#262, 4diac-ide#3132, adclz/rk#116, rusty#2035 again")
        refs = sitegen.upstream_refs(text)
        self.assertEqual(refs, [("Autonomy-Logic/STruCpp", 262), ("PLC-lang/rusty", 2035), ("adclz/rk", 116),
                                ("beremiz/matiec", 54), ("eclipse-4diac/4diac-ide", 3132), ("ironplc/ironplc", 2615)])

    def test_relative_links_point_to_github(self):
        md = "[x](conformance/ops/a.st), [y](https://e.org), [z](#anchor), [w](notes/comparison.md#totals)"
        out = sitegen.rewrite_links(md)
        self.assertIn(f"[x]({sitegen.BLOB}/conformance/ops/a.st)", out)
        self.assertIn("[y](https://e.org)", out)
        self.assertIn("[z](#anchor)", out)
        self.assertIn(f"[w]({sitegen.BLOB}/notes/comparison.md#totals)", out)

    def test_results_rows_get_links_and_badges(self):
        table = "| test | IronPLC | matiec | note |\n|---|---|---|---|\n| timers/ton | PASS | **FAIL** (cycle 4) | a **FAIL** in a note |\n"
        out = sitegen.results_rows(table, columns=2)
        self.assertIn('[timers/ton]({{< relref "/tests/timers/ton" >}})', out)
        self.assertIn('{{< badge "PASS" >}}', out)
        self.assertIn('{{< badge "FAIL" >}} (cycle 4)', out)
        self.assertIn("a **FAIL** in a note", out)       # the note column is left alone
        self.assertIn("| test | IronPLC | matiec | note |", out)

    def test_description_from_leading_comment(self):
        st = "(* MUX whose selector\n   is a MUX call. *)\nPROGRAM main\nEND_PROGRAM\n"
        self.assertEqual(sitegen.description(st), "MUX whose selector is a MUX call.")


class Generation(unittest.TestCase):
    def generate(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix="sitegen-"))
        sitegen.generate(ROOT, out)
        return out / "content"

    def test_one_page_per_test_and_runtime(self):
        out = self.generate()
        tests = sorted(ROOT.glob("conformance/*/*.st"))
        pages = sorted(p for p in (out / "tests").glob("*/*.md") if p.name != "_index.md")
        self.assertEqual(len(pages), len(tests))
        for rt in sitegen.RUNTIMES:
            self.assertTrue((out / "runtimes" / f"{rt}.md").exists(), rt)
            self.assertNotIn("weight: 0\n", (out / "runtimes" / f"{rt}.md").read_text())   # Hugo sorts 0 last
        self.assertIn('linkTitle: "not_compare"', (out / "tests" / "ops" / "not_compare.md").read_text())
        page = (out / "tests" / "ops" / "not_compare.md").read_text()
        self.assertIn("(NOT b) = c", page)            # the source
        self.assertIn("q1=TRUE q2=FALSE", page)       # the trace
        self.assertIn("FAIL", page)                   # matiec's verdict
        for name in ("_index.md", "results.md", "upstream.md"):
            self.assertTrue((out / name).exists(), name)

    def test_deterministic(self):
        a, b = self.generate().parent, self.generate().parent
        fa = {p.relative_to(a): p.read_bytes() for p in a.rglob("*") if p.is_file()}
        fb = {p.relative_to(b): p.read_bytes() for p in b.rglob("*") if p.is_file()}
        self.assertEqual(fa, fb)

    def test_no_stray_shortcodes(self):
        # Hugo would execute "{{<" even inside a code block
        out = self.generate()
        for p in out.rglob("*.md"):
            body = p.read_text()
            for line in body.splitlines():
                if "{{<" in line:
                    self.assertRegex(line, r"\{\{< (relref|badge|stats) ", f"{p}: {line}")

    def test_llms_files(self):
        out = self.generate()
        static = out.parent / "static"
        self.assertTrue((static / "llms.txt").exists())
        full = (static / "llms-full.txt").read_text()
        self.assertIn("ops/not_compare", full)


if __name__ == "__main__":
    unittest.main()
