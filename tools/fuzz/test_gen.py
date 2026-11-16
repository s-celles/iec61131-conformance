#!/usr/bin/env python3
"""Check the string and array oracle and the exclusions used to investigate divergences.

Run with python3 -I tools/fuzz/test_gen.py; no compiler required.
"""
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen


class Strings(unittest.TestCase):
    def test_table_34(self):
        examples = [
            ("CONCAT", ["ab", "CD", "ef", "GH"], "abCDefGH"),
            ("LEFT", ["abcde", 2], "ab"),
            ("RIGHT", ["abcde", 0], ""),
            ("MID", ["abcde", 2, 2], "bc"),
            ("INSERT", ["abcde", "XY", 2], "abXYcde"),
            ("INSERT", ["abcde", "XY", 5], "abcdeXY"),
            ("DELETE", ["abcde", 4, 2], "a"),
            ("REPLACE", ["abcde", "XY", 1, 2], "aXYcde"),
            ("LEN", [""], 0),
            ("FIND", ["abc", "bc"], 2),
            ("FIND", ["abc", "zz"], 0),
        ]
        for fn, args, expected in examples:
            with self.subTest(fn=fn, args=args):
                self.assertEqual(gen.iec_str(fn, args), expected)

    def test_invalid_ranges_and_capacity(self):
        for fn, args in [
            ("CONCAT", ["a" * 40, "b" * 40, "c"]),
            ("LEFT", ["abc", 4]),
            ("RIGHT", ["abc", -1]),
            ("MID", ["abc", 1, 0]),
            ("DELETE", ["abc", 2, 3]),
            ("INSERT", ["abc", "x", 4]),
            ("REPLACE", ["abc", "x", 4, 1]),
            ("FIND", ["abc", ""]),
        ]:
            with self.subTest(fn=fn, args=args):
                with self.assertRaises(gen.Undefined):
                    gen.iec_str(fn, args)

    def test_nested_concat_length_is_signed(self):
        s = ("call", "CONCAT", [("lit", "STRING", x) for x in ("a", "b", "c")])
        e = ("bin", "-", ("call", "LEN", [s]), ("lit", "INT", 5))
        self.assertEqual(gen.type_of(e, {}), "INT")
        self.assertEqual(gen.evaluate(e, {}, {}), -2)

    def test_known_string_operations_can_be_excluded(self):
        # Inspect expressions, including those in branches not executed by a
        # generated trace: an excluded construct must never reach the compiler.
        excluded = {"string_insert", "string_replace", "string_int", "ext_concat"}
        types = {"s": "STRING", "i": "INT", "b": "BOOL"}
        g = gen.Gen(random.Random(7), types, excluded)
        def calls(e):
            if e[0] == "call":
                yield e
            for part in e[1:]:
                for child in part if isinstance(part, list) else [part]:
                    if isinstance(child, tuple):
                        yield from calls(child)

        for _ in range(300):
            for ty in ("STRING", "INT"):
                e = g.expr(ty, 3)
                text = gen.render(e)
                self.assertNotIn("INSERT(", text)
                self.assertNotIn("REPLACE(", text)
                for call in calls(e):
                    if call[1] == "CONCAT":
                        self.assertEqual(len(call[2]), 2)
                if ty == "INT":
                    self.assertNotIn("LEN(", text)
                    self.assertNotIn("FIND(", text)


def walk(e):
    if isinstance(e, tuple):
        yield e
        for part in e[1:]:
            for child in part if isinstance(part, list) else [part]:
                yield from walk(child)


def stmt_exprs(stmts):
    """Every expression of a statement list, conditions and indices included."""
    for s in stmts:
        k = s[0]
        if k == "assign":
            yield s[2]
        elif k == "aassign":
            yield from s[3]
            yield s[4]
        elif k == "if":
            for cond, body in s[1]:
                yield cond
                yield from stmt_exprs(body)
            yield from stmt_exprs(s[2] or [])
        elif k == "case":
            yield s[1]
            for _, body in s[2]:
                yield from stmt_exprs(body)
            yield from stmt_exprs(s[3] or [])
        elif k == "for":
            yield from stmt_exprs(s[4])


class Arrays(unittest.TestCase):
    A0 = ("aref", "a0", "INT", [("lit", "INT", -2)])

    def env(self):
        return {"a0": {(i,): 10 * i for i in range(-2, 3)},
                "m0": {(i, j): 10 * i + j for i in range(0, 2) for j in range(1, 4)},
                "x": 3}

    def test_element_read(self):
        types = {"x": "INT"}
        self.assertEqual(gen.evaluate(self.A0, self.env(), types), -20)
        m = ("aref", "m0", "INT", [("lit", "INT", 1), ("bin", "-", ("var", "x"), ("lit", "INT", 1))])
        self.assertEqual(gen.evaluate(m, self.env(), types), 12)
        self.assertEqual(gen.type_of(m, types), "INT")
        self.assertEqual(gen.render(m), "m0[1, (x - 1)]")
        self.assertEqual(gen.render(self.A0), "a0[(-2)]")

    def test_index_out_of_bounds_is_undefined(self):
        # ed.3 6.4.4.3 / 7.3.1: a subscript outside the declared subrange is an error
        env = self.env()
        for idx in (-3, 3):
            with self.subTest(idx=idx):
                with self.assertRaises(gen.Undefined):
                    gen.evaluate(("aref", "a0", "INT", [("lit", "INT", idx)]), env, {})
        with self.assertRaises(gen.Undefined):
            gen.evaluate(("aref", "m0", "INT", [("lit", "INT", 0), ("lit", "INT", 0)]), env, {})

    def test_element_write(self):
        env = self.env()
        s = ("aassign", "a0", "INT", [("var", "x")], ("lit", "INT", -1))
        with self.assertRaises(gen.Undefined):
            gen.exec_stmts([s], env, {"x": "INT"})
        env["x"] = 1
        gen.exec_stmts([s], env, {"x": "INT"})
        self.assertEqual(env["a0"][(1,)], -1)
        self.assertEqual(gen.render_stmts([s], 0), ["a0[x] := (-1);"])

    def test_an_element_reads_state(self):
        # a divisor that reads an array element is not a constant expression
        self.assertTrue(gen.has_var(self.A0))

    def test_constant_subscripts_are_within_bounds(self):
        bounds = {name: dims for name, (_, dims, _) in gen.PROFILES["arrays"]["arrays"].items()}
        seen = 0
        for seed in range(40):
            pg = gen.ProgGen(random.Random(seed), "arrays")
            for e in stmt_exprs(pg.program()):
                for x in walk(e):
                    if x[0] != "aref":
                        continue
                    seen += 1
                    for (lo, hi), idx in zip(bounds[x[1]], x[3]):
                        if not gen.has_var(idx):
                            self.assertTrue(lo <= gen.evaluate(idx, {}, {}) <= hi, gen.render(x))
        self.assertGreater(seen, 40)

    def test_element_as_in_out_and_output(self):
        env = self.env()
        el = ("aref", "a0", "INT", [("var", "x")])
        env["x"] = 1
        tick = ("ucall", "F_TICK", [el, ("lit", "INT", 5)], "pos")
        self.assertEqual(gen.evaluate(tick, env, {"x": "INT"}), 15)
        self.assertEqual(env["a0"][(1,)], 15)
        self.assertEqual(gen.effects(tick), [("a0", False)])
        self.assertEqual(gen.render(tick), "F_TICK(a0[x], 5)")
        dm = ("ucall", "F_DM", [("lit", "INT", 7), ("lit", "INT", 2), ("aref", "m0", "INT", [("lit", "INT", 0), ("lit", "INT", 3)])], "formal")
        self.assertEqual(gen.evaluate(dm, env, {}), 3)
        self.assertEqual(env["m0"][(0, 3)], 1)
        # the array an element call writes must not be read elsewhere
        self.assertFalse(gen.well_defined(("bin", "+", tick, self.A0)))
        self.assertTrue(gen.well_defined(("bin", "+", tick, ("var", "x"))))

    def test_array_calls_profile_passes_elements(self):
        texts = [m[0] for m in (gen.make(s, 5, profile="array_calls") for s in range(1, 41)) if m]
        self.assertGreater(len(texts), 30)
        joined = "\n".join(texts)
        self.assertRegex(joined, r"F_TICK\((n := )?(a0|a1|m0)\[")
        self.assertRegex(joined, r"r => (a0|a1|m0)\[")

    def test_element_arguments_can_be_excluded(self):
        for seed in range(1, 41):
            m = gen.make(seed, 5, profile="array_calls", excl=["array_elem_args"])
            if m:
                self.assertNotRegex(m[0], r"F_TICK\((n := )?(a0|a1|m0)\[")
                self.assertNotRegex(m[0], r"r => (a0|a1|m0)\[")

    def test_program_declares_arrays(self):
        made = [gen.make(seed, 5, profile="arrays") for seed in range(1, 21)]
        made = [m for m in made if m]
        self.assertGreater(len(made), 15)
        st = made[0][0]
        self.assertIn("a0 : ARRAY[-2..2] OF INT := [", st)
        self.assertIn("m0 : ARRAY[0..1, 1..3] OF INT;", st)
        self.assertTrue(any("[" in line and ":=" in line and line.strip().startswith(("a0[", "a1[", "m0["))
                            for st, _ in made for line in st.splitlines()))


class Structs(unittest.TestCase):
    P0X = ("fld", ("var", "p0"), "x", "INT")

    def env(self):
        return {"p0": {"x": 1, "y": 5, "ok": False},
                "p1": {"x": 2, "y": 5, "ok": True},
                "pa": {(i,): {"x": 10 * i, "y": 5, "ok": False} for i in range(3)},
                "i": 2}

    def test_field_read(self):
        types = {"p0": "PT", "i": "INT"}
        self.assertEqual(gen.evaluate(self.P0X, self.env(), types), 1)
        self.assertEqual(gen.render(self.P0X), "p0.x")
        self.assertEqual(gen.type_of(self.P0X, types), "INT")
        el = ("fld", ("aref", "pa", "PT", [("var", "i")]), "x", "INT")
        self.assertEqual(gen.evaluate(el, self.env(), types), 20)
        self.assertEqual(gen.render(el), "pa[i].x")
        self.assertTrue(gen.has_var(self.P0X))
        self.assertEqual(gen.reads(el), {"pa", "i"})

    def test_struct_assignment_copies(self):
        # ed.3 7.3.2 / 6.4.4.4: assigning a structured variable copies its value
        env, types = self.env(), {"p0": "PT", "p1": "PT"}
        gen.exec_stmts([("assign", "p0", ("var", "p1")),
                        ("lassign", ("fld", ("var", "p1"), "x", "INT"), ("lit", "INT", 9))], env, types)
        self.assertEqual(env["p0"]["x"], 2)
        self.assertEqual(env["p1"]["x"], 9)
        el = ("aref", "pa", "PT", [("lit", "INT", 0)])
        gen.exec_stmts([("lassign", el, ("var", "p0")),
                        ("lassign", self.P0X, ("lit", "INT", -3))], env, types)
        self.assertEqual(env["pa"][(0,)]["x"], 2)
        self.assertEqual(gen.render_stmts([("lassign", el, ("var", "p0"))], 0), ["pa[0] := p0;"])

    def test_field_out_of_range_subscript(self):
        el = ("fld", ("aref", "pa", "PT", [("lit", "INT", 3)]), "y", "INT")
        with self.assertRaises(gen.Undefined):
            gen.evaluate(el, self.env(), {})

    def test_field_as_in_out(self):
        env = self.env()
        tick = ("ucall", "F_TICK", [self.P0X, ("lit", "INT", 4)], "pos")
        self.assertEqual(gen.evaluate(tick, env, {}), 5)
        self.assertEqual(env["p0"]["x"], 5)
        self.assertEqual(gen.effects(tick), [("p0", False)])
        self.assertFalse(gen.well_defined(("bin", "+", tick, ("fld", ("var", "p0"), "y", "INT"))))

    def test_program_declares_types(self):
        made = [m for m in (gen.make(s, 5, profile="structs") for s in range(1, 31)) if m]
        self.assertGreater(len(made), 20)
        st = made[0][0]
        self.assertIn("TYPE\n  PT : STRUCT", st)
        self.assertIn("    y : INT := 5;", st)
        self.assertIn("p1 : PT := (x := 2, ok := TRUE);", st)
        self.assertIn("pa : ARRAY[0..2] OF PT;", st)
        joined = "\n".join(m[0] for m in made)
        self.assertRegex(joined, r"\b(p0|p1|pa\[[^]]+\])\.(x|y|ok)\b")
        self.assertRegex(joined, r"\n\s*(p0|p1|pa\[[^]]+\]) := (p0|p1|pa\[[^]]+\]);")

    def test_struct_calls_profile_and_exclusions(self):
        made = [m[0] for m in (gen.make(s, 5, profile="struct_calls") for s in range(1, 41)) if m]
        self.assertRegex("\n".join(made), r"F_TICK\((n := )?(p0|p1|pa\[[^]]+\])\.(x|y)")
        for s in range(1, 41):
            m = gen.make(s, 5, profile="struct_calls",
                         excl=["struct_field_args", "struct_copy", "struct_init"])
            if m:
                self.assertNotRegex(m[0], r"F_TICK\((n := )?(p0|p1|pa\[[^]]+\])\.")
                self.assertNotRegex(m[0], r"r => (p0|p1|pa\[[^]]+\])\.")
                self.assertNotRegex(m[0], r"\n\s*(p0|p1|pa\[[^]]+\]) := (p0|p1|pa\[[^]]+\]);")
                self.assertNotIn(":= (x :=", m[0])


if __name__ == "__main__":
    unittest.main()
