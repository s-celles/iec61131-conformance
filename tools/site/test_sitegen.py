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

    def test_relative_links_resolve_from_the_file(self):
        out = sitegen.rewrite_links("[r](../README.md), [s](spec.md)", "docs/guide.md")
        self.assertIn(f"[r]({sitegen.BLOB}/README.md)", out)
        self.assertIn(f"[s]({sitegen.BLOB}/docs/spec.md)", out)

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


class Findings(unittest.TestCase):
    def test_items_of_a_section(self):
        md = ("intro\n\n1. **First thing** (x#1): text\n   more text\n2. **Second `code`**: other\n\n"
              "Also observed, not a deviation: a remark.\n\n10. **Tenth**: last\n")
        items = sitegen.numbered_items(md)
        self.assertEqual([(n, t) for n, t, _ in items], [(1, "First thing"), (2, "Second `code`"), (10, "Tenth")])
        self.assertIn("more text", items[0][2])
        self.assertNotIn("Also observed", items[1][2])

    def test_status(self):
        self.assertEqual(sitegen.status("(Resolved 2026-11-02) F_TRIG", ""), "fixed")
        self.assertEqual(sitegen.status("REPLACE", "inserts only L. Fixed upstream in 4454518 (PR #46)."), "fixed")
        self.assertEqual(sitegen.status("(Not a defect) CTU counts past PV", ""), "not a defect")
        self.assertEqual(sitegen.status("(Limitation) One program instance", ""), "limitation")
        self.assertEqual(sitegen.status("NOT on a BYTE", "(beremiz/matiec#54): stage 4"), "reported")
        self.assertEqual(sitegen.status("A MUX crashes", "(`ops/x`, not yet reported upstream)"), "not reported")

    def test_registry_of_the_repository(self):
        site = sitegen.Site(ROOT)
        f = {x["id"]: x for x in site.findings}
        self.assertEqual(len(f), len(site.findings))          # ids are unique
        self.assertGreater(len(f), 90)
        self.assertEqual(f["rusty-10"]["status"], "not reported")
        self.assertIn(("beremiz/matiec", 54), f["matiec-19"]["refs"])
        self.assertEqual(f["matiec-19"]["status"], "reported")
        self.assertEqual(f["ironplc-6"]["status"], "fixed")
        self.assertEqual(f["ironplc-7"]["status"], "not a defect")
        self.assertIn("ops/mux_nested_selector", f["rusty-10"]["tests"])
        self.assertNotIn("matiec-1", f)                       # an IronPLC behaviour, finding ironplc-1
        self.assertEqual(f["matiec-11"]["status"], "fixed")

    def test_pages(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix="sitegen-"))
        sitegen.generate(ROOT, out)
        c = out / "content"
        index = (c / "findings" / "_index.md").read_text()
        self.assertIn('class="filterable"', index)
        self.assertIn('relref "/findings/rusty-10"', index)
        page = (c / "findings" / "rusty-10.md").read_text()
        self.assertIn("MUX(MUX(k, a, b), a, b)", page)
        self.assertIn('relref "/tests/ops/mux_nested_selector"', page)
        test = (c / "tests" / "ops" / "mux_nested_selector.md").read_text()
        self.assertIn('relref "/findings/rusty-10"', test)
        self.assertIn('class="filterable"', (c / "results.md").read_text())


class Wording(unittest.TestCase):
    def test_disclaimer_and_provenance(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix="sitegen-"))
        sitegen.generate(ROOT, out)
        home = (out / "content" / "_index.md").read_text()
        self.assertIn("non-commercial", home)
        self.assertIn("not checked against", home)            # the derivations came from an AI
        self.assertIn("scanard-banner.svg", home)
        self.assertNotIn("by hand", home)
        footer = (ROOT / "site/layouts/_partials/custom/footer.html").read_text()
        self.assertIn("non-commercial", footer)
        self.assertIn("non-commercial", (out / "static" / "llms.txt").read_text())


class Properties(unittest.TestCase):
    def test_block_tests_show_the_property_check(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix="sitegen-"))
        sitegen.generate(ROOT, out)
        ton = (out / "content" / "tests" / "timers" / "ton.md").read_text()
        self.assertIn("## Properties", ton)
        self.assertIn("TON.Q", ton)                    # RuSTy's late Q, PLC-lang/rusty#2032
        self.assertIn("expected trace", ton)
        self.assertNotIn("## Properties", (out / "content" / "tests" / "ops" / "not_compare.md").read_text())


class History(unittest.TestCase):
    def test_totals_in_both_historical_formats(self):
        new = "Totals (90 tests, 72 with `status: conformant`): conformant tests passed, IronPLC 50/72; matiec 62/72; rk 51/72. 19 of the 90"
        old = "Totals: IronPLC 38/51 conformant pass; matiec 43/51; OpenPLC's matiec fork\n40/51; RuSTy RUSTY_TOTAL/35. No test"
        self.assertEqual(sitegen.history_totals(new), (72, {"IronPLC": 50, "matiec": 62, "rk": 51}))
        self.assertEqual(sitegen.history_totals(old), (51, {"IronPLC": 38, "matiec": 43, "OpenPLC's matiec": 40}))

    def test_history_page(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix="sitegen-"))
        sitegen.generate(ROOT, out)
        page = (out / "content" / "history.md").read_text()
        self.assertIn("<svg", page)
        self.assertIn("RuSTy", page)
        self.assertIn("| date | commit |", page)   # the data behind the charts
        rows = sitegen.history(ROOT)
        self.assertGreater(len(rows), 10)
        self.assertEqual(rows[-1]["tests"], len(list(ROOT.glob("conformance/*/*.st"))))
        dates = [r["date"] for r in rows]
        self.assertEqual(dates, sorted(dates))

    def test_site_workflow_fetches_the_history(self):
        self.assertIn("fetch-depth: 0", (ROOT / ".github/workflows/site.yml").read_text())


if __name__ == "__main__":
    unittest.main()
