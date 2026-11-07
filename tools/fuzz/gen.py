#!/usr/bin/env python3
"""Random, well-defined ST programs for differential testing.

A program is one PROGRAM main with inputs, outputs and retained internal
variables of the types of the chosen profile, and a body of assignments,
IF, CASE and bounded FOR statements over the operators and standard
functions whose meaning IEC 61131-3 fixes completely:

  core  INT and BOOL: + - * / MOD, comparisons, AND OR XOR NOT, ABS MIN
        MAX LIMIT SEL MUX (tables 29/30/32, 71);
  time  core plus TIME: + and - between TIMEs (kept >= 0), TIME * INT,
        comparisons, MIN MAX LIMIT SEL MUX (table 30); no division (its
        resolution is implementation-dependent);
  wide  core plus DINT and UINT with the same operators and the
        *_TO_* conversions between the three (table 22, in-range only),
        and BYTE and WORD with AND OR XOR NOT, SHL SHR ROL ROR by a
        constant below the width, BYTE_TO_WORD, and = <> (tables 30, 31).
  calls core plus user-defined POUs used inside expressions: F_LIN (pure,
        called positionally or formally with the inputs in any order),
        F_TICK (adds to its VAR_IN_OUT and returns it), F_DM (returns
        a / b and writes a MOD b to its VAR_OUTPUT), and a function block
        instance acc0 (s := x - prev; prev := x) called as a statement and
        read through acc0.s (6.6.1, 6.6.2; 7.3.2). An expression holds at
        most one call with a side effect, never under AND/OR/XOR (whose
        short-circuit evaluation ed.3 7.3.2 leaves open), and does not read
        the variable that call writes elsewhere (the order in which operands
        are evaluated is not fixed either).

A reference evaluator runs the program on random inputs; any step that
would leave the type's range, divide by zero, convert out of range or
select MUX out of range is "undefined" and the whole program is
discarded, so what remains is a program whose expected trace follows
from the standard alone (the evaluator transcribes those tables, it is
not a runtime).

    python3 -I tools/fuzz/gen.py --seed 7 --profile wide out_dir

writes out_dir/fuzz_7.st and out_dir/fuzz_7.trace (SPEC.md version 1).
Every binary sub-expression is parenthesised, so operator precedence is
not what is tested here (conformance/ops/precedence does that). Literals
outside an INT context are typed (DINT#5, UINT#5, 16#0F).
"""

import argparse
import pathlib
import random

RANGE = {
    "INT": (-32768, 32767), "DINT": (-2**31, 2**31 - 1), "UINT": (0, 65535),
    "BYTE": (0, 255), "WORD": (0, 65535),
    "TIME": (0, 10**7),   # milliseconds; kept non-negative (SPEC.md writes T#<n>ms)
}
WIDTH = {"BYTE": 8, "WORD": 16}
INT_TYPES = ("INT", "DINT", "UINT")
ORDERED_TYPES = INT_TYPES + ("TIME",)
BIT_TYPES = ("BYTE", "WORD")
LIT_RANGE = {"INT": (-20, 20), "DINT": (-20, 20), "UINT": (0, 20), "BYTE": (0, 255), "WORD": (0, 65535), "TIME": (0, 5000)}
IN_RANGE = {"INT": (-50, 50), "DINT": (-100000, 100000), "UINT": (0, 200), "BYTE": (0, 255), "WORD": (0, 65535), "TIME": (0, 100000)}

EXCLUDABLE = {
    "ext_minmax": "MIN/MAX with more than two inputs (ironplc#2548)",
    "literal_args": "a bare literal as a function argument (STruC++ template deduction)",
    "case_call": "a CASE selector that is not a plain variable (STruC++)",
    "limit_inverted": "LIMIT with MN > MX: matiec, STruC++ and RuSTy return MN (matiec#50, rusty#2040)",
    "mux_expr": "MUX inputs that are expressions rather than variables (STruCpp#262)",
    "not_expr": "NOT applied to anything but a variable (STruCpp#263)",
    "conversions": "the *_TO_* conversions between INT, DINT and UINT, and BYTE_TO_WORD",
    "shifts": "SHL SHR ROL ROR",
    "typed_literals": "DINT#, UINT#, BYTE# and WORD# literals: plain decimal / 16# is written instead",
    "time_functions": "MIN MAX LIMIT SEL MUX on TIME (ironplc#2555)",
    "time_literal_ms": "TIME literals with a millisecond part: whole seconds are written instead (beremiz/matiec#44 on AArch64)",
    "time_mul": "TIME * INT (beremiz/matiec#51; rk refuses it)",
    "mux_unsigned": "MUX on UINT (rk has no unsigned MUX overload)",
    "std_formal": "formal calls of standard functions, LIMIT(MX := .., IN := .., MN := ..) (profile calls; RuSTy: rusty#2035)",
}

# formal parameter names of the standard functions (ed.3 tables 29-32)
STD_PARAMS = {"ABS": ["IN"], "LIMIT": ["MN", "IN", "MX"], "SEL": ["G", "IN0", "IN1"]}


def std_param_names(fn, n):
    if fn in STD_PARAMS:
        return STD_PARAMS[fn]
    if fn in ("MIN", "MAX"):
        return [f"IN{i + 1}" for i in range(n)]
    if fn == "MUX":
        return ["K"] + [f"IN{i}" for i in range(n - 1)]
    return None


def formalize(e, rng):
    """Turn some standard function calls in e into formal calls with their
    arguments in a random order: ("call", fn, args, order)."""
    if not isinstance(e, tuple):
        return e
    parts = [e[0]]
    for x in e[1:]:
        if isinstance(x, tuple):
            parts.append(formalize(x, rng))
        elif isinstance(x, list):
            parts.append([formalize(y, rng) for y in x])
        else:
            parts.append(x)
    e = tuple(parts)
    if e[0] == "call" and std_param_names(e[1], len(e[2])) and rng.random() < 0.3:
        order = list(range(len(e[2])))
        rng.shuffle(order)
        e = e + (tuple(order),)
    return e


class Undefined(Exception):
    pass


def chk(ty, v):
    lo, hi = RANGE[ty]
    if not lo <= v <= hi:
        raise Undefined(f"{ty} range")
    return v


def iec_div(ty, a, b):
    if b == 0:
        raise Undefined("division by zero")
    q = abs(a) // abs(b)
    return chk(ty, q if (a >= 0) == (b >= 0) else -q)


def iec_mod(ty, a, b):
    if b == 0:
        raise Undefined("MOD by zero")
    return chk(ty, a - iec_div(ty, a, b) * b)


def has_var(e):
    if e[0] == "var":
        return True
    for x in e[1:]:
        if isinstance(x, tuple) and has_var(x):
            return True
        if isinstance(x, list) and any(has_var(y) for y in x):
            return True
    return False


def folds_to_zero(e, types):
    try:
        return evaluate(e, {}, types) == 0
    except Undefined:
        return True

# ---------------------------------------------------------------- expressions
#   ("lit", ty, v)  ("var", name)  ("neg", e)  ("not", e)  ("bnot", e)
#   ("bin", op, l, r)   ("call", fn, [args])   ("conv", from, to, e)
#   ("shift", fn, e, n)
# Types of variables are in a dict name -> type shared by generator,
# evaluator and renderer.


class Gen:
    def __init__(self, rng, types, excl=(), effect_vars=()):
        self.rng = rng
        self.types = types
        self.excl = set(excl)
        # INT variables a user function may write (VAR_IN_OUT / VAR_OUTPUT);
        # empty unless the profile has user-defined POUs
        self.effect_vars = list(effect_vars)

    def vars_of(self, ty):
        return [n for n, t in self.types.items() if t == ty]

    def lit(self, ty):
        lo, hi = LIT_RANGE[ty]
        v = self.rng.randint(lo, hi)
        if ty == "TIME" and "time_literal_ms" in self.excl:
            v = v - v % 1000
        return ("lit", ty, v)

    def var_or_lit(self, ty):
        vs = self.vars_of(ty)
        if vs and self.rng.random() < 0.7:
            return ("var", self.rng.choice(vs))
        return self.lit(ty)

    def arg(self, ty, depth):
        e = self.bit_expr(ty, depth) if ty in BIT_TYPES else self.int_expr(ty, depth)
        if "literal_args" in self.excl and e[0] == "lit":
            vs = self.vars_of(ty)
            e = ("var", self.rng.choice(vs)) if vs else e
        return e

    def int_expr(self, ty, depth):
        r = self.rng
        if depth <= 0 or r.random() < 0.3:
            return self.var_or_lit(ty)
        k = r.random()
        if ty == "TIME" and k < 0.5:
            # table 30: TIME + TIME, TIME - TIME, TIME * ANY_NUM (the INT factor
            # is kept non-negative by ABS); the difference must stay >= 0
            op = r.choice(["+", "+", "-"] + ([] if "time_mul" in self.excl else ["*"]))
            l = self.int_expr(ty, depth - 1)
            rr = ("call", "ABS", [self.int_expr("INT", depth - 1)]) if op == "*" else self.int_expr(ty, depth - 1)
            return ("bin", op, l, rr)
        if ty == "TIME" and "time_functions" in self.excl:
            return self.var_or_lit(ty)
        if ty == "TIME" and k < 0.62:
            k = 0.75   # no negation, no conversion: fall through to the functions
        if k < 0.5:
            op = r.choice(["+", "+", "-", "-", "*", "/", "MOD"])
            l, rr = self.int_expr(ty, depth - 1), self.int_expr(ty, depth - 1)
            if op in ("/", "MOD"):
                # a constant divisor must not fold to zero (compilers reject it)
                # nor hit an undefined step of its own
                while not has_var(rr) and folds_to_zero(rr, self.types):
                    rr = self.int_expr(ty, depth - 1)
            return ("bin", op, l, rr)
        if ty == "INT" and self.effect_vars and r.random() < 0.3:
            return self.user_call(depth)
        if k < 0.58 and ty != "UINT":
            return ("neg", self.int_expr(ty, depth - 1))
        if k < 0.7 and "conversions" not in self.excl and len([t for t in INT_TYPES if self.vars_of(t)]) > 1:
            src = r.choice([t for t in INT_TYPES if t != ty and self.vars_of(t)])
            return ("conv", src, ty, self.arg(src, depth - 1))
        fn = r.choice(["ABS", "MIN", "MAX", "LIMIT", "SEL", "MUX"])
        if fn == "ABS":
            if ty in ("UINT", "TIME"):
                fn = "MIN"
            else:
                return ("call", fn, [self.arg(ty, depth - 1)])
        if fn in ("MIN", "MAX"):
            n = 2 if "ext_minmax" in self.excl else r.choice([2, 2, 3])
            return ("call", fn, [self.arg(ty, depth - 1) for _ in range(n)])
        if fn == "LIMIT":
            if "limit_inverted" in self.excl:
                a, b = self.arg(ty, depth - 1), self.arg(ty, depth - 1)
                return ("call", fn, [("call", "MIN", [a, b]), self.arg(ty, depth - 1), ("call", "MAX", [a, b])])
            return ("call", fn, [self.arg(ty, depth - 1) for _ in range(3)])
        if fn == "SEL":
            return ("call", fn, [self.bool_expr(depth - 1), self.arg(ty, depth - 1), self.arg(ty, depth - 1)])
        if ty == "UINT" and "mux_unsigned" in self.excl:
            return ("call", "SEL", [self.bool_expr(depth - 1), self.arg(ty, depth - 1), self.arg(ty, depth - 1)])
        n = r.choice([2, 3, 4])
        # K is an INT kept in range by construction: ABS(k) MOD n
        k_expr = ("bin", "MOD", ("call", "ABS", [self.int_expr("INT", depth - 1)]), ("lit", "INT", n))
        if "mux_expr" in self.excl and self.vars_of(ty):
            return ("call", "MUX", [k_expr] + [("var", r.choice(self.vars_of(ty))) for _ in range(n)])
        return ("call", "MUX", [k_expr] + [self.arg(ty, depth - 1) for _ in range(n)])

    def user_call(self, depth):
        r = self.rng
        fn = r.choice(["F_LIN", "F_LIN", "F_TICK", "F_DM"])
        if fn == "F_LIN":
            return ("ucall", fn, [self.int_expr("INT", depth - 1), self.int_expr("INT", depth - 1)],
                    r.choice(["pos", "formal", "formal_rev"]))
        if fn == "F_TICK":
            return ("ucall", fn, [("var", r.choice(self.effect_vars)), self.int_expr("INT", depth - 1)],
                    r.choice(["pos", "formal"]))
        b = self.int_expr("INT", depth - 1)
        while not has_var(b) and folds_to_zero(b, self.types):
            b = self.int_expr("INT", depth - 1)
        return ("ucall", fn, [self.int_expr("INT", depth - 1), b, ("var", r.choice(self.effect_vars))],
                r.choice(["formal", "formal_rev"]))

    def bit_expr(self, ty, depth):
        r = self.rng
        if depth <= 0 or r.random() < 0.3:
            return self.var_or_lit(ty)
        k = r.random()
        if k < 0.5:
            op = r.choice(["AND", "OR", "XOR"])
            return ("bin", op, self.bit_expr(ty, depth - 1), self.bit_expr(ty, depth - 1))
        if k < 0.62:
            if "not_expr" in self.excl and self.vars_of(ty):
                return ("bnot", ("var", r.choice(self.vars_of(ty))))
            return ("bnot", self.bit_expr(ty, depth - 1))
        if k < 0.85 and "shifts" not in self.excl:
            fn = r.choice(["SHL", "SHR", "ROL", "ROR"])
            return ("shift", fn, self.arg(ty, depth - 1), r.randint(0, WIDTH[ty] - 1))
        if ty == "WORD" and "conversions" not in self.excl and self.vars_of("BYTE"):
            return ("conv", "BYTE", "WORD", self.arg("BYTE", depth - 1))
        return ("bin", r.choice(["AND", "OR"]), self.bit_expr(ty, depth - 1), self.var_or_lit(ty))

    def bool_expr(self, depth):
        r = self.rng
        bools = self.vars_of("BOOL")
        if depth <= 0 or r.random() < 0.25:
            if bools and r.random() < 0.7:
                return ("var", r.choice(bools))
            return ("lit", "BOOL", r.choice([True, False]))
        k = r.random()
        if k < 0.4:
            ty = r.choice([t for t in ORDERED_TYPES if self.vars_of(t)] or ["INT"])
            op = r.choice(["<", "<=", ">", ">=", "=", "<>"])
            return ("bin", op, self.int_expr(ty, depth - 1), self.int_expr(ty, depth - 1))
        if k < 0.5 and any(self.vars_of(t) for t in BIT_TYPES):
            ty = r.choice([t for t in BIT_TYPES if self.vars_of(t)])
            return ("bin", r.choice(["=", "<>"]), self.bit_expr(ty, depth - 1), self.bit_expr(ty, depth - 1))
        if k < 0.85:
            op = r.choice(["AND", "OR", "XOR"])
            return ("bin", op, self.bool_expr(depth - 1), self.bool_expr(depth - 1))
        if "not_expr" in self.excl and bools:
            return ("not", ("var", r.choice(bools)))
        return ("not", self.bool_expr(depth - 1))

    def expr(self, ty, depth):
        if ty == "BOOL":
            return self.bool_expr(depth)
        if ty in BIT_TYPES:
            return self.bit_expr(ty, depth)
        return self.int_expr(ty, depth)


def render(e, excl=()):
    k = e[0]
    if k == "lit":
        ty, v = e[1], e[2]
        if ty == "BOOL":
            return "TRUE" if v else "FALSE"
        if ty in BIT_TYPES:
            hexa = f"16#{v:0{WIDTH[ty] // 4}X}"
            return hexa if "typed_literals" in excl else f"{ty}#{hexa}"
        if ty == "TIME":
            return f"T#{v}ms"
        if ty == "INT" or "typed_literals" in excl:
            return str(v) if v >= 0 else f"(-{-v})"
        return f"{ty}#{v}" if v >= 0 else f"(-{ty}#{-v})"
    if k == "var":
        return e[1]
    if k == "neg":
        return f"(-{render(e[1], excl)})"
    if k in ("not", "bnot"):
        return f"(NOT {render(e[1], excl)})"
    if k == "bin":
        return f"({render(e[2], excl)} {e[1]} {render(e[3], excl)})"
    if k == "call":
        if len(e) > 3:   # formal call, arguments in the order e[3]
            names = std_param_names(e[1], len(e[2]))
            return f"{e[1]}({', '.join(f'{names[i]} := {render(e[2][i], excl)}' for i in e[3])})"
        return f"{e[1]}({', '.join(render(a, excl) for a in e[2])})"
    if k == "conv":
        return f"{e[1]}_TO_{e[2]}({render(e[3], excl)})"
    if k == "shift":
        return f"{e[1]}({render(e[2], excl)}, {e[3]})"
    if k == "ucall":
        fn, args, form = e[1], [render(a, excl) for a in e[2]], e[3]
        if form == "pos":
            return f"{fn}({', '.join(args)})"
        names = {"F_LIN": ["a", "b"], "F_TICK": ["n", "d"], "F_DM": ["a", "b"]}[fn]
        parts = [f"{n} := {v}" for n, v in zip(names, args)]
        if form == "formal_rev":
            parts.reverse()
        if fn == "F_DM":
            parts.append(f"r => {args[2]}")
        return f"{fn}({', '.join(parts)})"
    raise ValueError(k)


def effects(e, under_bool=False, acc=None):
    """[(var written, under a short-circuitable operator)] for the calls with
    a side effect in e."""
    acc = [] if acc is None else acc
    if not isinstance(e, tuple):
        return acc
    if e[0] == "ucall" and e[1] in ("F_TICK", "F_DM"):
        acc.append((e[2][0][1] if e[1] == "F_TICK" else e[2][2][1], under_bool))
    sc = e[0] == "bin" and e[1] in ("AND", "OR", "XOR")
    for x in e[1:]:
        for y in (x if isinstance(x, list) else [x]):
            if isinstance(y, tuple):
                effects(y, under_bool or sc, acc)
    return acc


def reads(e, acc=None):
    """Variables read by e, leaving out the one a side-effect call writes."""
    acc = set() if acc is None else acc
    if not isinstance(e, tuple):
        return acc
    if e[0] == "var":
        acc.add(e[1])
        return acc
    kids = e[2] if e[0] == "ucall" else [y for x in e[1:] for y in (x if isinstance(x, list) else [x])]
    if e[0] == "ucall" and e[1] == "F_TICK":
        kids = kids[1:]
    if e[0] == "ucall" and e[1] == "F_DM":
        kids = kids[:2]
    for y in kids:
        reads(y, acc)
    return acc


def well_defined(e):
    eff = effects(e)
    if not eff:
        return True
    if len(eff) > 1 or eff[0][1]:
        return False
    return eff[0][0] not in reads(e)


def type_of(e, types):
    k = e[0]
    if k == "lit":
        return e[1]
    if k == "var":
        return types[e[1]]
    if k in ("neg", "bnot"):
        return type_of(e[1], types)
    if k == "not":
        return "BOOL"
    if k == "bin":
        return "BOOL" if e[1] in ("<", "<=", ">", ">=", "=", "<>") else type_of(e[2], types)
    if k == "call":
        return type_of(e[2][-1], types)
    if k == "conv":
        return e[2]
    if k == "shift":
        return type_of(e[2], types)
    if k == "ucall":
        return "INT"
    raise ValueError(k)


def evaluate(e, env, types):
    k = e[0]
    if k == "lit":
        return e[2]
    if k == "var":
        return env[e[1]]
    if k == "neg":
        return chk(type_of(e, types), -evaluate(e[1], env, types))
    if k == "not":
        return not evaluate(e[1], env, types)
    if k == "bnot":
        ty = type_of(e, types)
        return (~evaluate(e[1], env, types)) & RANGE[ty][1]
    if k == "bin":
        op = e[1]
        a = evaluate(e[2], env, types)
        b = evaluate(e[3], env, types)
        ty = type_of(e[2], types)
        if ty in BIT_TYPES and op in ("AND", "OR", "XOR"):
            return {"AND": a & b, "OR": a | b, "XOR": a ^ b}[op]
        if op == "+":
            return chk(ty, a + b)
        if op == "-":
            return chk(ty, a - b)
        if op == "*":
            return chk(ty, a * b)
        if op == "/":
            return iec_div(ty, a, b)
        if op == "MOD":
            return iec_mod(ty, a, b)
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
        args = [evaluate(a, env, types) for a in e[2]]
        ty = type_of(e, types)
        if fn == "ABS":
            return chk(ty, abs(args[0]))
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
    if k == "conv":
        return chk(e[2], evaluate(e[3], env, types))
    if k == "shift":
        fn, n = e[1], e[3]
        ty = type_of(e, types)
        w, mask = WIDTH[ty], RANGE[ty][1]
        v = evaluate(e[2], env, types)
        if fn == "SHL":
            return (v << n) & mask
        if fn == "SHR":
            return v >> n
        if fn == "ROL":
            return ((v << n) | (v >> (w - n))) & mask if n else v
        if fn == "ROR":
            return ((v >> n) | (v << (w - n))) & mask if n else v
        raise ValueError(fn)
    if k == "ucall":
        fn = e[1]
        if fn == "F_LIN":   # F_LIN := 2 * a - b
            a, b = evaluate(e[2][0], env, types), evaluate(e[2][1], env, types)
            return chk("INT", chk("INT", 2 * a) - b)
        if fn == "F_TICK":  # n := n + d; F_TICK := n
            n = e[2][0][1]
            d = evaluate(e[2][1], env, types)
            env[n] = chk("INT", env[n] + d)
            return env[n]
        if fn == "F_DM":    # F_DM := a / b; r := a MOD b
            a, b = evaluate(e[2][0], env, types), evaluate(e[2][1], env, types)
            q = iec_div("INT", a, b)
            env[e[2][2][1]] = iec_mod("INT", a, b)
            return q
        raise ValueError(fn)
    raise ValueError(k)

USER_POUS = """FUNCTION F_LIN : INT
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  F_LIN := 2 * a - b;
END_FUNCTION

FUNCTION F_TICK : INT
  VAR_IN_OUT
    n : INT;
  END_VAR
  VAR_INPUT
    d : INT;
  END_VAR
  n := n + d;
  F_TICK := n;
END_FUNCTION

FUNCTION F_DM : INT
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    r : INT;
  END_VAR
  F_DM := a / b;
  r := a MOD b;
END_FUNCTION

FUNCTION_BLOCK ACC
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    s : INT;
  END_VAR
  VAR
    prev : INT;
  END_VAR
  s := x - prev;
  prev := x;
END_FUNCTION_BLOCK
"""


# ----------------------------------------------------------------- statements
# ("assign", name, expr) ("if", [(cond, [stmts])...], [else_stmts] or None)
# ("case", expr, [((lo, hi), [stmts])...], [else_stmts] or None)
# ("for", var, a, b, [stmts])  with constants a <= b

PROFILES = {
    "core": {
        "inputs": [("i0", "INT"), ("i1", "INT"), ("b0", "BOOL")],
        "outputs": [("o0", "INT"), ("o1", "INT"), ("o2", "INT"), ("q0", "BOOL"), ("q1", "BOOL")],
        "internal": [("v0", "INT"), ("v1", "INT"), ("f0", "BOOL")],
    },
    "time": {
        "inputs": [("i0", "INT"), ("i1", "INT"), ("t0", "TIME"), ("t1", "TIME"), ("b0", "BOOL")],
        "outputs": [("o0", "INT"), ("ot", "TIME"), ("ot2", "TIME"), ("q0", "BOOL"), ("q1", "BOOL")],
        "internal": [("v0", "INT"), ("vt", "TIME"), ("f0", "BOOL")],
    },
    "wide": {
        "inputs": [("i0", "INT"), ("i1", "INT"), ("d0", "DINT"), ("u0", "UINT"), ("by0", "BYTE"), ("w0", "WORD"), ("b0", "BOOL")],
        "outputs": [("o0", "INT"), ("o1", "INT"), ("od", "DINT"), ("ou", "UINT"), ("ob", "BYTE"), ("ow", "WORD"), ("q0", "BOOL"), ("q1", "BOOL")],
        "internal": [("v0", "INT"), ("vd", "DINT"), ("vu", "UINT"), ("vb", "BYTE"), ("vw", "WORD"), ("f0", "BOOL")],
    },
    "calls": {
        "inputs": [("i0", "INT"), ("i1", "INT"), ("b0", "BOOL")],
        "outputs": [("o0", "INT"), ("o1", "INT"), ("o2", "INT"), ("q0", "BOOL"), ("q1", "BOOL")],
        "internal": [("v0", "INT"), ("v1", "INT"), ("f0", "BOOL")],
        "pous": True,
    },
}


class ProgGen:
    def __init__(self, rng, profile="core", excl=()):
        self.rng = rng
        p = PROFILES[profile]
        self.inputs, self.outputs, self.internal = p["inputs"], p["outputs"], p["internal"]
        self.loop_var = "ix"
        self.types = {n: t for n, t in self.inputs + self.outputs + self.internal}
        self.writable = self.outputs + self.internal
        self.excl = set(excl)
        self.pous = p.get("pous", False)
        self.effect_vars = [n for n, t in self.writable if t == "INT"] if self.pous else []
        if self.pous:
            self.types["acc0.s"] = "INT"   # read-only: the FB instance's output

    def stmts(self, n, depth, in_loop=False):
        return [self.stmt(depth, in_loop) for _ in range(n)]

    def stmt(self, depth, in_loop):
        r = self.rng
        types = dict(self.types)
        if in_loop:
            types[self.loop_var] = "INT"
        g = Gen(r, types, self.excl, self.effect_vars)
        k = r.random()
        if self.pous and r.random() < 0.12:
            return ("fbcall", "acc0", self.defined(g, lambda: g.int_expr("INT", 2)))
        if depth <= 0 or k < 0.55:
            name, ty = r.choice(self.writable)
            return ("assign", name, self.defined(g, lambda: g.expr(ty, 3)))
        if k < 0.75:
            branches = [(self.defined(g, lambda: g.bool_expr(2)), self.stmts(r.randint(1, 2), depth - 1, in_loop))
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
            sel = ("var", r.choice(g.vars_of("INT"))) if "case_call" in self.excl else self.defined(g, lambda: g.int_expr("INT", 2))
            return ("case", sel, labels, els)
        if in_loop:
            name, ty = r.choice(self.writable)
            return ("assign", name, self.defined(g, lambda: g.expr(ty, 2)))
        a = r.randint(-2, 2)
        b = a + r.randint(0, 3)
        return ("for", self.loop_var, a, b, self.stmts(r.randint(1, 2), depth - 1, True))

    def defined(self, g, make_expr):
        """An expression whose value does not depend on evaluation order or
        short-circuiting (see well_defined); without user calls after 20 tries."""
        for _ in range(20):
            e = make_expr()
            if well_defined(e):
                if self.pous and "std_formal" not in self.excl:
                    e = formalize(e, self.rng)
                return e
        saved, g.effect_vars = g.effect_vars, []
        e = make_expr()
        g.effect_vars = saved
        return e

    def program(self, n_stmts=6):
        return self.stmts(n_stmts, 2)


def render_stmts(stmts, ind, excl=()):
    out = []
    pad = "  " * ind
    for s in stmts:
        k = s[0]
        if k == "assign":
            out.append(f"{pad}{s[1]} := {render(s[2], excl)};")
        elif k == "if":
            first = True
            for cond, body in s[1]:
                out.append(f"{pad}{'IF' if first else 'ELSIF'} {render(cond, excl)} THEN")
                out += render_stmts(body, ind + 1, excl)
                first = False
            if s[2] is not None:
                out.append(f"{pad}ELSE")
                out += render_stmts(s[2], ind + 1, excl)
            out.append(f"{pad}END_IF;")
        elif k == "case":
            out.append(f"{pad}CASE {render(s[1], excl)} OF")
            for (lo, hi), body in s[2]:
                lab = f"{lo}" if lo == hi else f"{lo}..{hi}"
                out.append(f"{pad}  {lab}:")
                out += render_stmts(body, ind + 2, excl)
            if s[3] is not None:
                out.append(f"{pad}ELSE")
                out += render_stmts(s[3], ind + 1, excl)
            out.append(f"{pad}END_CASE;")
        elif k == "for":
            out.append(f"{pad}FOR {s[1]} := {s[2]} TO {s[3]} DO")
            out += render_stmts(s[4], ind + 1, excl)
            out.append(f"{pad}END_FOR;")
        elif k == "fbcall":
            out.append(f"{pad}{s[1]}(x := {render(s[2], excl)});")
        else:
            raise ValueError(k)
    return out


def exec_stmts(stmts, env, types):
    for s in stmts:
        k = s[0]
        if k == "assign":
            env[s[1]] = evaluate(s[2], env, types)
        elif k == "if":
            for cond, body in s[1]:
                if evaluate(cond, env, types):
                    exec_stmts(body, env, types)
                    break
            else:
                if s[2] is not None:
                    exec_stmts(s[2], env, types)
        elif k == "case":
            v = evaluate(s[1], env, types)
            for (lo, hi), body in s[2]:
                if lo <= v <= hi:
                    exec_stmts(body, env, types)
                    break
            else:
                if s[3] is not None:
                    exec_stmts(s[3], env, types)
        elif k == "for":
            for i in range(s[2], s[3] + 1):
                env[s[1]] = i
                exec_stmts(s[4], env, types)
            env.pop(s[1], None)
        elif k == "fbcall":
            x = evaluate(s[2], env, types)
            env[s[1] + ".s"] = chk("INT", x - env[s[1] + ".prev"])
            env[s[1] + ".prev"] = x
        else:
            raise ValueError(k)


def fmt(ty, v):
    if ty == "BOOL":
        return "TRUE" if v else "FALSE"
    if ty == "TIME":
        return f"T#{v}ms"
    if ty in BIT_TYPES:
        return f"16#{v:0{WIDTH[ty] // 4}X}"
    return str(v)


def make(seed, cycles, n_stmts=6, tries=200, excl=(), profile="core"):
    """Return (st_text, trace_text) for a seed, or None if every candidate
    program hit an undefined step."""
    rng = random.Random(seed)
    for attempt in range(tries):
        pg = ProgGen(rng, profile, excl)
        body = pg.program(n_stmts)
        types = dict(pg.types)
        types[pg.loop_var] = "INT"
        env = {n: (False if t == "BOOL" else 0) for n, t in pg.types.items()}
        if pg.pous:
            env["acc0.prev"] = 0
        records = []
        try:
            for c in range(cycles):
                ins = {}
                for n, t in pg.inputs:
                    if t == "BOOL":
                        ins[n] = rng.choice([True, False])
                    else:
                        lo, hi = IN_RANGE[t]
                        ins[n] = rng.randint(lo, hi)
                env.update(ins)
                exec_stmts(body, env, types)
                outs = {n: env[n] for n, _ in pg.outputs}
                records.append((c, ins, outs))
        except Undefined:
            continue
        st = ["(* generated by tools/fuzz/gen.py, profile %s, seed %d, attempt %d *)" % (profile, seed, attempt)]
        if pg.pous:
            st += [USER_POUS]
        st += ["PROGRAM main", "  VAR_INPUT"]
        st += [f"    {n} : {t};" for n, t in pg.inputs]
        st += ["  END_VAR", "  VAR_OUTPUT"]
        st += [f"    {n} : {t};" for n, t in pg.outputs]
        st += ["  END_VAR", "  VAR"]
        st += [f"    {n} : {t};" for n, t in pg.internal] + [f"    {pg.loop_var} : INT;"]
        if pg.pous:
            st += ["    acc0 : ACC;"]
        st += ["  END_VAR"]
        st += render_stmts(body, 1, excl)
        st += ["END_PROGRAM", ""]
        tr = [f"# generated by tools/fuzz/gen.py, profile {profile}, seed {seed}: expected values from the reference evaluator",
              "period_ms: 100", "program: main",
              "inputs: " + " ".join(n for n, _ in pg.inputs),
              "outputs: " + " ".join(n for n, _ in pg.outputs),
              "status: conformant", "---"]
        for c, ins, outs in records:
            tr.append(f"{c} " + " ".join(f"{n}={fmt(pg.types[n], v)}" for n, v in ins.items()) + " => " +
                      " ".join(f"{n}={fmt(pg.types[n], v)}" for n, v in outs.items()))
        return "\n".join(st), "\n".join(tr) + "\n"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cycles", type=int, default=5)
    ap.add_argument("--stmts", type=int, default=6)
    ap.add_argument("--profile", choices=sorted(PROFILES), default="core")
    ap.add_argument("--exclude", default="", help="comma list of " + ", ".join(EXCLUDABLE))
    ap.add_argument("out_dir")
    a = ap.parse_args()
    r = make(a.seed, a.cycles, a.stmts, excl=[x for x in a.exclude.split(",") if x], profile=a.profile)
    if r is None:
        raise SystemExit("no well-defined program found for this seed")
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"fuzz_{a.seed}.st").write_text(r[0])
    (out / f"fuzz_{a.seed}.trace").write_text(r[1])
    print(out / f"fuzz_{a.seed}.st")


if __name__ == "__main__":
    main()
