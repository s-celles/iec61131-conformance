"""Parser for the .trace format of SPEC.md (Python port of harness/ironplc/src/trace.rs)."""
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Union


class Status(Enum):
    CONFORMANT = "conformant"
    IMPLEMENTATION_DEFINED = "implementation-defined"


REAL_RE = re.compile(r"^-?[0-9]+\.[0-9]+([eE][-+]?[0-9]+)?$")
REAL_TOL = {"REAL": 1e-6, "LREAL": 1e-12}
STR_ESC = {"$": b"$", "'": b"'", "L": b"\n", "N": b"\n", "P": b"\x0c", "R": b"\r", "T": b"\t"}


def decode_string_literal(s):
    """`'...'` with IEC escapes ($$ $' $L $N $P $R $T $xx), no raw space -> bytes."""
    if len(s) < 2 or s[0] != "'" or s[-1] != "'":
        raise ValueError(f"STRING value must be quoted with ': {s}")
    body, out, i = s[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c == "$":
            e = body[i + 1:i + 2].upper()
            if e in STR_ESC:
                out += STR_ESC[e]; i += 2
            else:
                out.append(int(body[i + 1:i + 3], 16)); i += 3
        elif c in " \t'":
            raise ValueError(f"STRING value may not contain a raw space, tab or quote: {s}")
        else:
            out += c.encode("latin-1"); i += 1
    return bytes(out)


def encode_string_literal(b):
    """bytes -> canonical `'...'`: printable ASCII raw, space as $20,
    $ and ' doubled/escaped, control characters as $L $P $R $T or $xx."""
    out = "'"
    for x in b:
        if x == 0x24: out += "$$"
        elif x == 0x27: out += "$'"
        elif x == 0x09: out += "$T"
        elif x == 0x0A: out += "$L"
        elif x == 0x0C: out += "$P"
        elif x == 0x0D: out += "$R"
        elif 0x21 <= x <= 0x7E: out += chr(x)
        else: out += f"${x:02X}"
    return out + "'"


@dataclass(frozen=True)
class Value:
    kind: str  # bool | int | time | bits | real | str | any
    v: int = 0
    width: int = 0  # bits: number of hex digits (2 BYTE, 4 WORD, 8 DWORD)
    text: str = ""  # real: the literal as written, printed back verbatim
    data: bytes = b""  # str: the decoded bytes

    @staticmethod
    def parse(s: str) -> "Value":
        if s == "?":
            return Value("any")
        if s == "TRUE":
            return Value("bool", 1)
        if s == "FALSE":
            return Value("bool", 0)
        if s.startswith("T#"):
            if not s.endswith("ms"):
                raise ValueError(f"TIME literal must be T#<n>ms: {s}")
            return Value("time", int(s[2:-2]))
        if s.startswith("'"):
            return Value("str", 0, 0, "", decode_string_literal(s))
        if REAL_RE.match(s) or s in ("inf", "-inf", "nan"):
            return Value("real", float(s), 0, s)
        if s.startswith("16#"):
            digits = s[3:]
            if len(digits) not in (2, 4, 8) or digits != digits.upper():
                raise ValueError(f"bit string literal must be 16# and 2, 4 or 8 upper-case hex digits: {s}")
            return Value("bits", int(digits, 16), len(digits))
        return Value("int", int(s))

    def __str__(self) -> str:
        if self.kind == "bool":
            return "TRUE" if self.v else "FALSE"
        if self.kind == "time":
            return f"T#{self.v}ms"
        if self.kind == "bits":
            return f"16#{self.v:0{self.width}X}"
        if self.kind == "real":
            return self.text
        if self.kind == "str":
            return encode_string_literal(self.data)
        if self.kind == "any":
            return "?"
        return str(self.v)

    def matches(self, actual_text, ty):
        """SPEC.md comparison: REAL/LREAL numerically within a relative
        tolerance (floored at 1.0), everything else by text."""
        if self.kind == "any":
            return True
        if self.kind == "str":
            # drivers print STRING outputs as #<hex bytes>; the Rust harness prints the literal
            if actual_text and actual_text.startswith("#"):
                return bytes.fromhex(actual_text[1:]) == self.data
            return actual_text == str(self)
        if self.kind != "real":
            return actual_text == str(self)
        try:
            a = float(actual_text.replace("-nan", "nan"))
        except (TypeError, ValueError):
            return False
        e = self.v
        if math.isnan(e) or math.isnan(a):
            return math.isnan(e) and math.isnan(a)
        if math.isinf(e) or math.isinf(a):
            return e == a
        return abs(a - e) <= REAL_TOL[ty] * max(abs(e), 1.0)


def canonical_actual(rhs, types):
    """Rewrite a driver's `name=#hex` STRING outputs as `'...'` literals."""
    if rhs.startswith("trap"):
        return rhs
    toks = []
    for tok in rhs.split():
        n, _, v = tok.partition("=")
        if v.startswith("#") and types.get(n, "").startswith("STRING"):
            v = encode_string_literal(bytes.fromhex(v[1:]))
        toks.append(f"{n}={v}" if _ else tok)
    return " ".join(toks)


@dataclass
class Record:
    cycle: int
    inputs: List[Tuple[str, Value]]
    expected: Union[str, List[Tuple[str, Value]]]  # "trap" or list
    line: int


@dataclass
class Trace:
    period_ms: int
    program: str
    inputs: List[str]
    outputs: List[str]
    status: Status
    reference: Optional[str]
    records: List[Record] = field(default_factory=list)


def _assign(tok: str, line: int) -> Tuple[str, Value]:
    if "=" not in tok:
        raise ValueError(f"line {line}: expected name=value, got '{tok}'")
    n, v = tok.split("=", 1)
    return n.lower(), Value.parse(v)


def parse_trace(text: str) -> Trace:
    header = {}
    records: List[Record] = []
    in_body = False
    next_cycle = 0
    saw_trap = False
    for idx, raw in enumerate(text.splitlines()):
        line = idx + 1
        l = raw.strip()
        if not l or l.startswith("#"):
            continue
        if not in_body:
            if l == "---":
                in_body = True
                continue
            k, v = l.split(":", 1)
            header[k.strip()] = v.strip()
            continue
        if saw_trap:
            raise ValueError(f"line {line}: records after a 'trap' record")
        lhs, rhs = l.split("=>", 1)
        toks = lhs.split()
        cycle = int(toks[0])
        if cycle != next_cycle:
            raise ValueError(f"line {line}: cycle {cycle} but expected {next_cycle}")
        next_cycle += 1
        inputs = []
        for tok in toks[1:]:
            n, v = _assign(tok, line)
            if v.kind == "any":
                raise ValueError(f"line {line}: '?' is not allowed as an input value")
            if any(m == n for m, _ in inputs):
                raise ValueError(f"line {line}: input '{n}' assigned twice")
            inputs.append((n, v))
        rhs = rhs.strip()
        if rhs == "trap":
            saw_trap = True
            expected: Union[str, List[Tuple[str, Value]]] = "trap"
        else:
            expected = [_assign(t, line) for t in rhs.split()]
        records.append(Record(cycle, inputs, expected, line))

    period_ms = int(header["period_ms"])
    if period_ms <= 0:
        raise ValueError("header: period_ms must be positive")
    inputs = header["inputs"].lower().split()
    outputs = header["outputs"].lower().split()
    status = Status(header.get("status", "conformant"))
    for r in records:
        for n, _ in r.inputs:
            if n not in inputs:
                raise ValueError(f"line {r.line}: '{n}' is not a declared input")
        if r.expected != "trap":
            for n, _ in r.expected:
                if n not in outputs:
                    raise ValueError(f"line {r.line}: '{n}' is not a declared output")
            for o in outputs:
                if sum(1 for n, _ in r.expected if n == o) != 1:
                    raise ValueError(f"line {r.line}: output '{o}' must appear exactly once")
    return Trace(period_ms, header.get("program", ""), inputs, outputs, status, header.get("reference"), records)
