#!/usr/bin/env python3
"""Random, well-defined ST programs for differential testing.

A program is one PROGRAM main with INT and BOOL inputs, outputs and
retained internal variables, and a body of assignments, IF, CASE and
bounded FOR statements over the operators and standard functions whose
meaning IEC 61131-3 fixes completely (table 29/30, 71: + - * / MOD,
comparisons, AND OR XOR NOT, ABS MIN MAX LIMIT SEL MUX). A reference
evaluator runs the program on random inputs; any step that would leave
the INT range, divide by zero or select MUX out of range is "undefined"
and the whole program is discarded, so what remains is a program whose
expected trace follows from the standard alone (the evaluator is a
transcription of those tables, not a runtime).

    python3 -I tools/fuzz/gen.py --seed 7 --cycles 5 out_dir

writes out_dir/fuzz_7.st and out_dir/fuzz_7.trace (SPEC.md version 1).
Every binary sub-expression is parenthesised, so operator precedence is
not what is tested here (conformance/ops/precedence does that).
"""

import argparse
import pathlib
import random

INT_MIN, INT_MAX = -32768, 32767


class Undefined(Exception):
    pass


def chk(v):
    if not INT_MIN <= v <= INT_MAX:
        raise Undefined("INT range")
    return v


def iec_div(a, b):
    if b == 0:
        raise Undefined("division by zero")
    q = abs(a) // abs(b)
    return chk(q if (a >= 0) == (b >= 0) else -q)


def iec_mod(a, b):
    if b == 0:
        raise Undefined("MOD by zero")
    return chk(a - iec_div(a, b) * b)


# ---------------------------------------------------------------- expressions
# An expression is a tuple; its first element is the node kind.
#   ("lit", v) ("var", name) ("neg", e) ("not", e)
#   ("bin", op, l, r)  op in + - * / MOD  (INT) or < <= > >= = <> (INT -> BOOL)
#                      or AND OR XOR (BOOL)
#   ("call", fn, [args])  ABS MIN MAX LIMIT (INT), SEL MUX (INT)


EXCLUDABLE = {
    "ext_minmax": "MIN/MAX with more than two inputs (ironplc#2548)",
    "literal_args": "a bare literal as a function argument (STruC++ template deduction)",
    "case_call": "a CASE selector that is not a plain variable (STruC++)",
    "limit_inverted": "LIMIT with MN > MX: matiec, STruC++ and RuSTy return MN",
    "mux_expr": "MUX inputs that are expressions rather than variables (STruC++)",
    "not_expr": "NOT applied to anything but a variable (STruC++)",
}


def has_var(e):
    return e[0] == "var" or any(has_var(x) for x in e[1:] if isinstance(x, tuple)) or \
        (e[0] == "call" and any(has_var(x) for x in e[2]))


class Gen:
    def __init__(self, rng, ints, bools, excl=()):
        self.rng = rng
        self.ints = ints      # readable INT variable names
        self.bools = bools    # readable BOOL variable names
        self.excl = set(excl)

    def arg(self, depth):
        e = self.int_expr(depth)
        if "literal_args" in self.excl and e[0] == "lit":
            e = ("var", self.rng.choice(self.ints)) if self.ints else ("neg", ("neg", e))
        return e

    def int_expr(self, depth):
        r = self.rng
        if depth <= 0 or r.random() < 0.3:
            if self.ints and r.random() < 0.7:
                return ("var", r.choice(self.ints))
            return ("lit", r.randint(-20, 20))
        k = r.random()
        if k < 0.55:
            op = r.choice(["+", "+", "-", "-", "*", "/", "MOD"])
            l, rr = self.int_expr(depth - 1), self.int_expr(depth - 1)
            if op in ("/", "MOD") and not has_var(rr):
                # a constant divisor must not fold to zero: compilers reject it
                while not has_var(rr) and evaluate(rr, {}) == 0:
                    rr = self.int_expr(depth - 1)
            return ("bin", op, l, rr)
        if k < 0.65:
            return ("neg", self.int_expr(depth - 1))
        fn = r.choice(["ABS", "MIN", "MAX", "LIMIT", "SEL", "MUX"])
        if fn == "ABS":
            return ("call", fn, [self.arg(depth - 1)])
        if fn in ("MIN", "MAX"):
            n = 2 if "ext_minmax" in self.excl else r.choice([2, 2, 3])
            return ("call", fn, [self.arg(depth - 1) for _ in range(n)])
        if fn == "LIMIT":
            if "limit_inverted" in self.excl:
                a, b = self.arg(depth - 1), self.arg(depth - 1)
                return ("call", fn, [("call", "MIN", [a, b]), self.arg(depth - 1), ("call", "MAX", [a, b])])
            return ("call", fn, [self.arg(depth - 1) for _ in range(3)])
        if fn == "SEL":
            return ("call", fn, [self.bool_expr(depth - 1), self.arg(depth - 1), self.arg(depth - 1)])
        n = r.choice([2, 3, 4])
        # K is kept in range by construction: (k MOD n) folded through ABS
        k_expr = ("bin", "MOD", ("call", "ABS", [self.int_expr(depth - 1)]), ("lit", n))
        if "mux_expr" in self.excl and self.ints:
            return ("call", "MUX", [k_expr] + [("var", r.choice(self.ints)) for _ in range(n)])
        return ("call", "MUX", [k_expr] + [self.arg(depth - 1) for _ in range(n)])

    def bool_expr(self, depth):
        r = self.rng
        if depth <= 0 or r.random() < 0.25:
            if self.bools and r.random() < 0.7:
                return ("var", r.choice(self.bools))
            return ("lit", r.choice([True, False]))
        k = r.random()
        if k < 0.45:
            op = r.choice(["<", "<=", ">", ">=", "=", "<>"])
            return ("bin", op, self.int_expr(depth - 1), self.int_expr(depth - 1))
        if k < 0.85:
            op = r.choice(["AND", "OR", "XOR"])
            return ("bin", op, self.bool_expr(depth - 1), self.bool_expr(depth - 1))
        if "not_expr" in self.excl and self.bools:
            return ("not", ("var", r.choice(self.bools)))
        return ("not", self.bool_expr(depth - 1))


def render(e):
    k = e[0]
    if k == "lit":
        v = e[1]
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        return str(v) if v >= 0 else f"(-{-v})"
    if k == "var":
        return e[1]
    if k == "neg":
        return f"(-{render(e[1])})"
    if k == "not":
        return f"(NOT {render(e[1])})"
    if k == "bin":
        return f"({render(e[2])} {e[1]} {render(e[3])})"
    if k == "call":
        return f"{e[1]}({', '.join(render(a) for a in e[2])})"
    raise ValueError(k)


def evaluate(e, env):
    k = e[0]
    if k == "lit":
        return e[1]
    if k == "var":
        return env[e[1]]
    if k == "neg":
        return chk(-evaluate(e[1], env))
    if k == "not":
        return not evaluate(e[1], env)
    if k == "bin":
        op = e[1]
        a = evaluate(e[2], env)
        b = evaluate(e[3], env)
        if op == "+":
            return chk(a + b)
        if op == "-":
            return chk(a - b)
        if op == "*":
            return chk(a * b)
        if op == "/":
            return iec_div(a, b)
        if op == "MOD":
            return iec_mod(a, b)
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == ">":
            return a > b
        if op == ">=":
            return a >= b
        if op == "=":
            return a == b
        if op == "<>":
            return a != b
        if op == "AND":
            return a and b
        if op == "OR":
            return a or b
        if op == "XOR":
            return a != b
        raise ValueError(op)
    if k == "call":
        fn = e[1]
        args = [evaluate(a, env) for a in e[2]]
        if fn == "ABS":
            return chk(abs(args[0]))
        if fn == "MIN":
            return min(args)
        if fn == "MAX":
            return max(args)
        if fn == "LIMIT":
            mn, v, mx = args
            return min(max(v, mn), mx)
        if fn == "SEL":
            return args[2] if args[0] else args[1]
        if fn == "MUX":
            kk = args[0]
            if not 0 <= kk < len(args) - 1:
                raise Undefined("MUX K out of range")
            return args[1 + kk]
        raise ValueError(fn)
    raise ValueError(k)


# ----------------------------------------------------------------- statements
# ("assign", name, expr) ("if", [(cond, [stmts])...], [else_stmts] or None)
# ("case", expr, [(labels, [stmts])...], [else_stmts] or None)
# ("for", var, a, b, [stmts])  with constants a <= b


class ProgGen:
    def __init__(self, rng, excl=(), n_in_int=2, n_in_bool=1, n_out_int=3, n_out_bool=2, n_var_int=2, n_var_bool=1):
        self.rng = rng
        self.excl = set(excl)
        self.in_int = [f"i{k}" for k in range(n_in_int)]
        self.in_bool = [f"b{k}" for k in range(n_in_bool)]
        self.out_int = [f"o{k}" for k in range(n_out_int)]
        self.out_bool = [f"q{k}" for k in range(n_out_bool)]
        self.var_int = [f"v{k}" for k in range(n_var_int)]
        self.var_bool = [f"f{k}" for k in range(n_var_bool)]
        self.ints = self.in_int + self.out_int + self.var_int
        self.bools = self.in_bool + self.out_bool + self.var_bool
        self.writable_int = self.out_int + self.var_int
        self.writable_bool = self.out_bool + self.var_bool
        self.loop_var = "ix"

    def stmts(self, n, depth, in_loop=False):
        return [self.stmt(depth, in_loop) for _ in range(n)]

    def stmt(self, depth, in_loop):
        r = self.rng
        ints = self.ints + ([self.loop_var] if in_loop else [])
        g = Gen(r, ints, self.bools, self.excl)
        k = r.random()
        if depth <= 0 or k < 0.55:
            if r.random() < 0.65:
                return ("assign", r.choice(self.writable_int), g.int_expr(3))
            return ("assign", r.choice(self.writable_bool), g.bool_expr(3))
        if k < 0.75:
            branches = [(g.bool_expr(2), self.stmts(r.randint(1, 2), depth - 1, in_loop))
                        for _ in range(r.randint(1, 2))]
            els = self.stmts(1, depth - 1, in_loop) if r.random() < 0.5 else None
            return ("if", branches, els)
        if k < 0.88:
            labels = []
            used = set()
            for _ in range(r.randint(1, 3)):
                lo = r.randint(-3, 3)
                hi = lo + r.choice([0, 0, 1, 2])
                if any(v in used for v in range(lo, hi + 1)):
                    continue
                used.update(range(lo, hi + 1))
                labels.append(((lo, hi), self.stmts(1, depth - 1, in_loop)))
            if not labels:
                labels = [((0, 0), self.stmts(1, depth - 1, in_loop))]
            els = self.stmts(1, depth - 1, in_loop) if r.random() < 0.6 else None
            sel = ("var", r.choice(ints)) if "case_call" in self.excl else g.int_expr(2)
            return ("case", sel, labels, els)
        if in_loop:
            return ("assign", r.choice(self.writable_int), g.int_expr(2))
        a = r.randint(-2, 2)
        b = a + r.randint(0, 3)
        return ("for", self.loop_var, a, b, self.stmts(r.randint(1, 2), depth - 1, True))

    def program(self, n_stmts=6):
        return self.stmts(n_stmts, 2)


def render_stmts(stmts, ind):
    out = []
    pad = "  " * ind
    for s in stmts:
        k = s[0]
        if k == "assign":
            out.append(f"{pad}{s[1]} := {render(s[2])};")
        elif k == "if":
            first = True
            for cond, body in s[1]:
                out.append(f"{pad}{'IF' if first else 'ELSIF'} {render(cond)} THEN")
                out += render_stmts(body, ind + 1)
                first = False
            if s[2] is not None:
                out.append(f"{pad}ELSE")
                out += render_stmts(s[2], ind + 1)
            out.append(f"{pad}END_IF;")
        elif k == "case":
            out.append(f"{pad}CASE {render(s[1])} OF")
            for (lo, hi), body in s[2]:
                lab = f"{lo}" if lo == hi else f"{lo}..{hi}"
                out.append(f"{pad}  {lab}:")
                out += render_stmts(body, ind + 2)
            if s[3] is not None:
                out.append(f"{pad}ELSE")
                out += render_stmts(s[3], ind + 1)
            out.append(f"{pad}END_CASE;")
        elif k == "for":
            out.append(f"{pad}FOR {s[1]} := {s[2]} TO {s[3]} DO")
            out += render_stmts(s[4], ind + 1)
            out.append(f"{pad}END_FOR;")
        else:
            raise ValueError(k)
    return out


def exec_stmts(stmts, env):
    for s in stmts:
        k = s[0]
        if k == "assign":
            env[s[1]] = evaluate(s[2], env)
        elif k == "if":
            for cond, body in s[1]:
                if evaluate(cond, env):
                    exec_stmts(body, env)
                    break
            else:
                if s[2] is not None:
                    exec_stmts(s[2], env)
        elif k == "case":
            v = evaluate(s[1], env)
            for (lo, hi), body in s[2]:
                if lo <= v <= hi:
                    exec_stmts(body, env)
                    break
            else:
                if s[3] is not None:
                    exec_stmts(s[3], env)
        elif k == "for":
            for i in range(s[2], s[3] + 1):
                env[s[1]] = i
                exec_stmts(s[4], env)
            env.pop(s[1], None)
        else:
            raise ValueError(k)


def fmt(v):
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return str(v)


def make(seed, cycles, n_stmts=6, tries=200, excl=()):
    """Return (st_text, trace_text) for a seed, or None if every candidate
    program hit an undefined step."""
    rng = random.Random(seed)
    for attempt in range(tries):
        pg = ProgGen(rng, excl)
        body = pg.program(n_stmts)
        env = {n: 0 for n in pg.ints} | {n: False for n in pg.bools}
        records = []
        try:
            for c in range(cycles):
                ins = {n: rng.randint(-50, 50) for n in pg.in_int} | {n: rng.choice([True, False]) for n in pg.in_bool}
                env.update(ins)
                exec_stmts(body, env)
                outs = {n: env[n] for n in pg.out_int + pg.out_bool}
                records.append((c, ins, outs))
        except Undefined:
            continue
        st = ["(* generated by tools/fuzz/gen.py, seed %d, attempt %d *)" % (seed, attempt), "PROGRAM main", "  VAR_INPUT"]
        st += [f"    {n} : INT;" for n in pg.in_int] + [f"    {n} : BOOL;" for n in pg.in_bool]
        st += ["  END_VAR", "  VAR_OUTPUT"]
        st += [f"    {n} : INT;" for n in pg.out_int] + [f"    {n} : BOOL;" for n in pg.out_bool]
        st += ["  END_VAR", "  VAR"]
        st += [f"    {n} : INT;" for n in pg.var_int] + [f"    {n} : BOOL;" for n in pg.var_bool] + [f"    {pg.loop_var} : INT;"]
        st += ["  END_VAR"]
        st += render_stmts(body, 1)
        st += ["END_PROGRAM", ""]
        tr = [f"# generated by tools/fuzz/gen.py, seed {seed}: expected values from the reference evaluator",
              "period_ms: 100", "program: main",
              "inputs: " + " ".join(pg.in_int + pg.in_bool),
              "outputs: " + " ".join(pg.out_int + pg.out_bool),
              "status: conformant", "---"]
        for c, ins, outs in records:
            tr.append(f"{c} " + " ".join(f"{n}={fmt(v)}" for n, v in ins.items()) + " => " + " ".join(f"{n}={fmt(v)}" for n, v in outs.items()))
        return "\n".join(st), "\n".join(tr) + "\n"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cycles", type=int, default=5)
    ap.add_argument("--stmts", type=int, default=6)
    ap.add_argument("--exclude", default="", help="comma list of " + ", ".join(EXCLUDABLE))
    ap.add_argument("out_dir")
    a = ap.parse_args()
    r = make(a.seed, a.cycles, a.stmts, excl=[x for x in a.exclude.split(",") if x])
    if r is None:
        raise SystemExit("no well-defined program found for this seed")
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"fuzz_{a.seed}.st").write_text(r[0])
    (out / f"fuzz_{a.seed}.trace").write_text(r[1])
    print(out / f"fuzz_{a.seed}.st")


if __name__ == "__main__":
    main()
