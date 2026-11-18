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

    def test_finer_exclusions(self):
        el = r"pa\[[^]]+\]"
        for s in range(1, 41):
            m = gen.make(s, 5, profile="struct_calls",
                         excl=["struct_elem_copy", "struct_field_inout", "array_elem_args"])
            if not m:
                continue
            body = m[0].split("PROGRAM main", 1)[1]
            # no element on either side of a whole-structure assignment
            self.assertNotRegex(body, rf"\n\s*{el} := (p0|p1|{el});")
            self.assertNotRegex(body, rf"\n\s*(p0|p1) := {el};")
            self.assertNotRegex(body, r"F_TICK\((n := )?(p0|p1|pa\[[^]]+\])\.")
            self.assertNotRegex(body, rf"r => {el}\.")
        # struct_field_inout still lets a field take a VAR_OUTPUT
        p = gen.PROFILES["struct_calls"]
        types = {n: t for n, t in p["inputs"] + p["outputs"] + p["internal"]}
        g = gen.Gen(random.Random(3), types, ["struct_field_inout"], ["o0", "v0"], p["arrays"], p["structs"])
        self.assertTrue(any(g.effect_target()[0] == "fld" for _ in range(50)))
        self.assertFalse(any(g.effect_target(inout=True)[0] == "fld" for _ in range(50)))


def nested_effect_calls(st):
    """(nested in a call's argument, as a MOD divisor) counts of the F_TICK /
    F_DM calls in the program body of st, found on the text: an independent
    oracle for the AST checks of gen.py. A function block call (acc0) is a
    statement, not an enclosing function call."""
    body = st.split("PROGRAM main", 1)[1]
    nested = divisor = 0
    for m in __import__("re").finditer(r"\b(F_TICK|F_DM)\(", body):
        i, depth, in_call = m.start(), 0, False
        j = i - 1
        while j >= 0 and not (body[j] == ";" and depth == 0) and body[j] != "\n":
            c = body[j]
            if c == ")":
                depth += 1
            elif c == "(":
                if depth == 0:
                    k = j
                    while k > 0 and body[k - 1] == " ":
                        k -= 1
                    e = k
                    while k > 0 and (body[k - 1].isalnum() or body[k - 1] == "_"):
                        k -= 1
                    name = body[k:e]
                    if name and name not in ("MOD", "AND", "OR", "XOR", "NOT", "IF", "ELSIF", "WHILE", "UNTIL", "CASE", "acc0"):
                        in_call = True
                else:
                    depth -= 1
            j -= 1
        nested += in_call
        divisor += bool(__import__("re").search(r"MOD\s*$", body[max(0, i - 6):i]))
    return nested, divisor


class EffectCalls(unittest.TestCase):
    TICK = ("ucall", "F_TICK", [("var", "o0"), ("lit", "INT", 1)], "pos")

    def test_predicates(self):
        t = self.TICK
        self.assertFalse(gen.effect_call_in_args(t))
        self.assertFalse(gen.effect_call_in_args(("bin", "+", ("var", "i0"), t)))
        self.assertTrue(gen.effect_call_in_args(("call", "ABS", [t])))
        self.assertTrue(gen.effect_call_in_args(("call", "MIN", [("var", "i0"), ("bin", "MOD", t, ("lit", "INT", 6))])))
        self.assertTrue(gen.effect_call_in_args(("ucall", "F_LIN", [("var", "i0"), t], "pos")))
        self.assertTrue(gen.effect_call_in_args(("conv", "INT", "DINT", t)))
        self.assertFalse(gen.effect_call_in_mod_divisor(("bin", "MOD", t, ("lit", "INT", 6))))
        self.assertFalse(gen.effect_call_in_mod_divisor(("bin", "/", ("var", "i0"), t)))
        self.assertTrue(gen.effect_call_in_mod_divisor(("bin", "MOD", ("var", "i0"), t)))
        self.assertTrue(gen.effect_call_in_mod_divisor(("bin", "MOD", ("var", "i0"), ("neg", t))))

    def test_calls_can_be_excluded(self):
        # matiec item 17 (a VAR_IN_OUT / VAR_OUTPUT call inside another call's
        # argument does not link) and item 16 (a call as MOD divisor is
        # generated twice): without the exclusions the profiles produce both,
        # with them neither reaches the compiler.
        for profile in ("calls", "struct_calls"):
            seen, seen_excl = [0, 0], [0, 0]
            for seed in range(1, 120):
                m = gen.make(seed, 3, 8, profile=profile)
                if m:
                    n, d = nested_effect_calls(m[0])
                    seen[0] += n
                    seen[1] += d
                m = gen.make(seed, 3, 8, profile=profile, excl=["call_in_args", "call_divisor"])
                if m:
                    n, d = nested_effect_calls(m[0])
                    seen_excl[0] += n
                    seen_excl[1] += d
            with self.subTest(profile=profile):
                self.assertGreater(seen[0], 0)
                if profile == "calls":   # a call as MOD divisor is rarer with structures
                    self.assertGreater(seen[1], 0)
                self.assertEqual(seen_excl, [0, 0])

    def test_exclusions_are_documented(self):
        self.assertIn("call_in_args", gen.EXCLUDABLE)
        self.assertIn("call_divisor", gen.EXCLUDABLE)


def mux_selectors_with_mux(st):
    """Number of MUX calls in the program body of st whose first argument
    (the selector K) contains another MUX call, found on the text."""
    body = st.split("PROGRAM main", 1)[1]
    n = 0
    for m in __import__("re").finditer(r"\bMUX\(", body):
        i = j = m.end()
        depth = 0
        while j < len(body):
            c = body[j]
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            elif c == "," and depth == 0:
                break
            j += 1
        n += "MUX(" in body[i:j]
    return n


class MuxSelector(unittest.TestCase):
    def test_mux_in_selector_can_be_excluded(self):
        # RuSTy item 10: a MUX call inside a MUX selector crashes plc.
        seen = seen_excl = 0
        for profile in ("core", "time", "strings"):
            for seed in range(1, 150):
                m = gen.make(seed, 3, 8, profile=profile)
                if m:
                    seen += mux_selectors_with_mux(m[0])
                m = gen.make(seed, 3, 8, profile=profile, excl=["mux_selector_call"])
                if m:
                    seen_excl += mux_selectors_with_mux(m[0])
        self.assertGreater(seen, 0)
        self.assertEqual(seen_excl, 0)
        self.assertIn("mux_selector_call", gen.EXCLUDABLE)


EXPR_KINDS = {"lit", "var", "neg", "not", "bnot", "bin", "call", "conv", "shift", "aref", "fld", "ucall"}


def expressions(node):
    """The expression trees inside a generated statement list."""
    if isinstance(node, list):
        for x in node:
            yield from expressions(x)
    elif isinstance(node, tuple):
        if node and isinstance(node[0], str) and node[0] in EXPR_KINDS:
            yield node
        else:
            for x in node[1:]:
                yield from expressions(x)


def constant_subtrees(e):
    if not isinstance(e, tuple):
        return
    if isinstance(e[0], str) and e[0] in EXPR_KINDS and not gen.has_var(e):
        yield e
        return
    for x in e[1:]:
        for y in (x if isinstance(x, list) else [x]):
            yield from constant_subtrees(y)


class ConstantRange(unittest.TestCase):
    def test_no_constant_out_of_range(self):
        # A constant subexpression whose value leaves its type, such as
        # UINT#6 - UINT#8, is rejected at compile time by IronPLC (P2026) and
        # matiec even in a branch that never runs, where the reference
        # evaluator does not see it (round 4, profile wide, seed 6071).
        bad = []
        for profile in ("wide", "core", "time"):
            for seed in range(6001, 6201):
                pg = gen.ProgGen(random.Random(seed), profile, ["literal_args"])
                body = pg.program(8)
                types = dict(pg.types)
                types[pg.loop_var] = "INT"
                for e in expressions(body):
                    for c in constant_subtrees(e):
                        try:
                            gen.evaluate(c, {}, types)
                        except gen.Undefined as u:
                            if str(u).split()[0] in gen.RANGE:
                                bad.append((profile, seed, gen.render(c)))
        self.assertEqual(bad, [])


def has_kind(e, kind):
    if not isinstance(e, tuple):
        return False
    if e and e[0] == kind:
        return True
    return any(has_kind(y, kind) for x in e[1:] for y in (x if isinstance(x, list) else [x]))


class BitNotCompare(unittest.TestCase):
    def test_not_in_compared_bit_strings_can_be_excluded(self):
        # matiec item 19 (beremiz/matiec#54): (NOT b) = c is computed in int.
        def compared(excl):
            n = 0
            for seed in range(1, 200):
                g = gen.Gen(random.Random(seed), {"b0": "BYTE", "w0": "WORD", "q0": "BOOL"}, excl)
                for _ in range(20):
                    e = g.bool_expr(3)
                    for sub in [e] + [y for x in e[1:] for y in (x if isinstance(x, list) else [x]) if isinstance(y, tuple)]:
                        if sub[0] == "bin" and sub[1] in ("=", "<>") and any(
                                isinstance(o, tuple) and gen.type_of(o, {"b0": "BYTE", "w0": "WORD", "q0": "BOOL"}) in gen.BIT_TYPES and has_kind(o, "bnot")
                                for o in sub[2:]):
                            n += 1
            return n
        self.assertGreater(compared([]), 0)
        self.assertEqual(compared(["bit_not_compare"]), 0)
        self.assertIn("bit_not_compare", gen.EXCLUDABLE)


if __name__ == "__main__":
    unittest.main()
