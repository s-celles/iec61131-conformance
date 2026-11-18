#!/usr/bin/env python3
"""Checks for the property monitors. Run with python3 -I tools/monitor/test_monitor.py."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import monitor

ROOT = pathlib.Path(__file__).resolve().parents[2]
F, T = False, True


def props(block, rows, **params):
    """Property names violated by a list of per-cycle pin dicts."""
    return sorted({v.prop for v in monitor.check_block(block, rows, 100, params)})


class Records(unittest.TestCase):
    def test_inputs_persist_and_values_parse(self):
        text = "period_ms: 100\ninputs: in\noutputs: q et\n---\n0 in=FALSE => q=FALSE et=T#0ms\n# c\n1 in=TRUE => q=FALSE et=T#0ms\n2 => q=TRUE et=T#1s\n"
        recs = monitor.parse_records(text.split("---", 1)[1], ["in"], ["q", "et"])
        self.assertEqual([r["in"] for r in recs], [F, T, T])
        self.assertEqual(recs[2]["et"], 1000)
        self.assertEqual(recs[2]["q"], T)


class EdgeAndBistables(unittest.TestCase):
    def test_r_trig(self):
        ok = [{"CLK": F, "Q": F}, {"CLK": T, "Q": T}, {"CLK": T, "Q": F}, {"CLK": F, "Q": F}]
        self.assertEqual(props("R_TRIG", ok), [])
        self.assertTrue(props("R_TRIG", [{"CLK": T, "Q": F}]))          # first evaluation with CLK TRUE is an edge

    def test_f_trig_first_evaluation(self):
        # ed.2 table 35 and its NOTE: Q at 1 after the first execution with CLK FALSE
        self.assertEqual(props("F_TRIG", [{"CLK": F, "Q": T}, {"CLK": F, "Q": F}, {"CLK": T, "Q": F}, {"CLK": F, "Q": T}]), [])
        self.assertTrue(props("F_TRIG", [{"CLK": F, "Q": F}]))

    def test_sr_rs(self):
        self.assertEqual(props("SR", [{"S1": T, "R": T, "Q1": T}, {"S1": F, "R": F, "Q1": T}, {"S1": F, "R": T, "Q1": F}]), [])
        self.assertTrue(props("SR", [{"S1": T, "R": T, "Q1": F}]))       # set dominant
        self.assertEqual(props("RS", [{"S": T, "R1": T, "Q1": F}, {"S": T, "R1": F, "Q1": T}]), [])
        self.assertTrue(props("RS", [{"S": T, "R1": T, "Q1": T}]))       # reset dominant


class Counters(unittest.TestCase):
    def test_ctu_counts_rising_edges(self):
        ok = [{"CU": T, "R": F, "Q": F, "CV": 1}, {"CU": T, "R": F, "Q": F, "CV": 1},
              {"CU": F, "R": F, "Q": F, "CV": 1}, {"CU": T, "R": F, "Q": F, "CV": 2}, {"CU": F, "R": T, "Q": F, "CV": 0}]
        self.assertEqual(props("CTU", ok, PV=3), [])
        self.assertIn("CTU.count", props("CTU", [{"CU": T, "R": F, "Q": F, "CV": 0}], PV=3))
        self.assertIn("CTU.Q", props("CTU", [{"CU": T, "R": F, "Q": F, "CV": 1}], PV=1))

    def test_ctu_wrap_is_a_violation_but_saturation_is_not(self):
        start = {"CU": F, "R": F, "Q": T, "CV": 32767}
        self.assertEqual(props("CTU", [start, {"CU": T, "R": F, "Q": T, "CV": 32767}], PV=3, CV0=32767), [])
        self.assertIn("CTU.count", props("CTU", [start, {"CU": T, "R": F, "Q": F, "CV": -32768}], PV=3, CV0=32767))

    def test_ctd_and_ctud(self):
        self.assertEqual(props("CTD", [{"CD": F, "LD": T, "Q": F, "CV": 3}, {"CD": T, "LD": F, "Q": F, "CV": 2}], PV=3), [])
        self.assertIn("CTD.load", props("CTD", [{"CD": F, "LD": T, "Q": F, "CV": 0}], PV=3))
        both = {"CU": T, "CD": T, "R": F, "LD": F, "QU": F, "QD": T, "CV": 0}
        self.assertEqual(props("CTUD", [both], PV=2), [])               # CU and CD together: no count
        self.assertIn("CTUD.count", props("CTUD", [dict(both, CV=1, QD=False)], PV=2))


class Timers(unittest.TestCase):
    def test_ton(self):
        ok = [{"IN": F, "Q": F, "ET": 0}, {"IN": T, "Q": F, "ET": 0}, {"IN": T, "Q": F, "ET": 100},
              {"IN": T, "Q": T, "ET": 200}, {"IN": T, "Q": T, "ET": 200}, {"IN": F, "Q": F, "ET": 0}]
        self.assertEqual(props("TON", ok, PT=200), [])
        late = ok[:3] + [{"IN": T, "Q": F, "ET": 200}]                    # ET reached PT, Q still FALSE
        self.assertIn("TON.Q", props("TON", late, PT=200))
        self.assertIn("TON.ET", props("TON", ok[:2] + [{"IN": T, "Q": F, "ET": 50}], PT=200))

    def test_tof(self):
        ok = [{"IN": F, "Q": F, "ET": 0}, {"IN": T, "Q": T, "ET": 0}, {"IN": F, "Q": T, "ET": 0},
              {"IN": F, "Q": T, "ET": 100}, {"IN": F, "Q": F, "ET": 200}, {"IN": F, "Q": F, "ET": 200}]
        self.assertEqual(props("TOF", ok, PT=200), [])
        self.assertIn("TOF.Q", props("TOF", [{"IN": F, "Q": T, "ET": 0}], PT=200))   # off-delay at power-up

    def test_tp(self):
        ok = [{"IN": T, "Q": T, "ET": 0}, {"IN": T, "Q": T, "ET": 100}, {"IN": T, "Q": F, "ET": 200},
              {"IN": T, "Q": F, "ET": 200}, {"IN": F, "Q": F, "ET": 0}, {"IN": T, "Q": T, "ET": 0}]
        self.assertEqual(props("TP", ok, PT=200), [])
        retrigger = ok[:4] + [{"IN": T, "Q": T, "ET": 0}]                 # new pulse without a new rising edge
        self.assertIn("TP.start", props("TP", retrigger, PT=200))
        self.assertIn("TP.ET", props("TP", ok[:3] + [{"IN": F, "Q": F, "ET": 200}], PT=200))

    def test_tp_end_with_in_false_is_open(self):
        # the diagram leaves ET open on the cycle the pulse ends with IN FALSE
        base = [{"IN": T, "Q": T, "ET": 0}, {"IN": F, "Q": T, "ET": 100}]
        for et in (0, 200):
            self.assertEqual(props("TP", base + [{"IN": F, "Q": F, "ET": et}, {"IN": F, "Q": F, "ET": 0}], PT=200), [])
        self.assertIn("TP.ET", props("TP", base + [{"IN": F, "Q": F, "ET": 100}], PT=200))

    def test_open_value_does_not_stop_the_check(self):
        recs = [{"in": T, "q": T, "et": 0, "_cycle": 0}, {"in": T, "q": T, "et": "?", "_cycle": 1},
                {"in": T, "q": True, "et": 300, "_cycle": 2}]       # PT = 300: Q still TRUE at ET = PT, after the "?"
        self.assertIn("TP.Q", {v.prop for v in monitor.check_records("timers/tp", [dict(r) for r in recs], 100)} | set())


class Repository(unittest.TestCase):
    def test_every_bound_test_exists(self):
        for name in monitor.BINDINGS:
            self.assertTrue((ROOT / "conformance" / f"{name}.st").exists(), name)

    def test_expected_traces_satisfy_the_properties(self):
        # the expected traces are AI-derived; the properties are read off the
        # ed.2 text (notes/trace-audit-2026-11-18.md): they must agree
        report = monitor.run(ROOT)
        bad = {(t, v.prop, v.cycle) for t, src, vs in report if src == "trace" for v in vs}
        self.assertEqual(bad, set())

    def test_known_runtime_deviations_are_caught(self):
        report = {(t, src): {v.prop for v in vs} for t, src, vs in monitor.run(ROOT)}
        self.assertIn("TON.Q", report[("timers/ton", "rusty")])           # PLC-lang/rusty#2032
        self.assertIn("TOF.Q", report[("timers/tof", "ironplc")])         # ironplc#2545
        self.assertIn("F_TRIG.Q", report[("edge/f_trig", "ironplc")])     # ironplc#2565
        self.assertEqual(report[("timers/ton", "matiec")], set())


if __name__ == "__main__":
    unittest.main()
