(* The selection and comparison functions on TIME: MIN, MAX and LIMIT
   are declared on ANY_ELEMENTARY (ed.3 table 32 / ed.2 table 27), SEL
   and MUX on ANY, and TIME is ordered (table 33 / ed.2 table 28), so all
   of them take TIME operands. ops/time_arith covers + - and the
   comparison operators; this is the functions. Found by tools/fuzz. *)
PROGRAM main
  VAR_INPUT
    a : TIME;
    b : TIME;
    k : INT;   (* 0..2 *)
  END_VAR
  VAR_OUTPUT
    lo  : TIME;   (* MIN(a, b) *)
    hi  : TIME;   (* MAX(a, b, T#1s) *)
    clamp : TIME;   (* LIMIT(T#100ms, a, T#5s) *)
    big : TIME;   (* SEL(a < b, a, b), the larger one *)
    pick : TIME;   (* MUX(k, a, b, a + b) *)
    less  : BOOL;   (* LT(a, b) *)
  END_VAR
  lo  := MIN(a, b);
  hi  := MAX(a, b, T#1s);
  clamp := LIMIT(T#100ms, a, T#5s);
  big := SEL(a < b, a, b);
  pick := MUX(k, a, b, a + b);
  less  := LT(a, b);
END_PROGRAM
