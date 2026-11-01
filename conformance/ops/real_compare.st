(* Comparison of REAL and LREAL values. *)
PROGRAM main
  VAR_INPUT
    x : REAL;
    y : REAL;
    a : LREAL;
    b : LREAL;
  END_VAR
  VAR_OUTPUT
    r_lt : BOOL;
    r_eq : BOOL;
    r_ge : BOOL;
    l_lt : BOOL;
    l_eq : BOOL;
    l_ne : BOOL;
  END_VAR
  r_lt := x < y;
  r_eq := x = y;
  r_ge := x >= y;
  l_lt := a < b;
  l_eq := a = b;
  l_ne := a <> b;
END_PROGRAM
