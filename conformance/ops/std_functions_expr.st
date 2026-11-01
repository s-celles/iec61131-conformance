(* Standard functions and NOT with expressions, not variables, as
   arguments: MUX whose inputs are arithmetic expressions and function
   results, SEL likewise, NOT applied to a comparison, to an XOR and to an
   AND of two comparisons.
   ops/std_functions uses variables only; this is the other spelling,
   found by tools/fuzz. *)
PROGRAM main
  VAR_INPUT
    k : INT;   (* 0..2 *)
    a : INT;
    b : INT;
    p : BOOL;
    q : BOOL;
  END_VAR
  VAR_OUTPUT
    m   : INT;    (* MUX(k, a + b, a * 2, MAX(a, b)) *)
    s   : INT;    (* SEL(a < b, a - b, b - a) *)
    n_eq  : BOOL; (* NOT (a = b) *)
    n_xor : BOOL; (* NOT (p XOR q) *)
    n_cmp : BOOL; (* NOT (a < b) AND q *)
    n_and : BOOL; (* NOT ((a < b) AND (b < 10)) *)
  END_VAR
  m     := MUX(k, a + b, a * 2, MAX(a, b));
  s     := SEL(a < b, a - b, b - a);
  n_eq  := NOT (a = b);
  n_xor := NOT (p XOR q);
  n_cmp := NOT (a < b) AND q;
  n_and := NOT ((a < b) AND (b < 10));
END_PROGRAM
