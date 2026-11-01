(* Numerical standard functions on REAL. *)
PROGRAM main
  VAR_INPUT
    x : REAL;
  END_VAR
  VAR_OUTPUT
    o_sqrt : REAL;
    o_abs  : REAL;
    o_exp  : REAL;
    o_ln   : REAL;
    o_sin  : REAL;
    o_cos  : REAL;
  END_VAR
  o_abs  := ABS(x);
  o_sqrt := SQRT(o_abs);
  o_exp  := EXP(x);
  o_ln   := LN(o_abs);
  o_sin  := SIN(x);
  o_cos  := COS(x);
END_PROGRAM
