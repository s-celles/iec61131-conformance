(* LREAL (binary64) arithmetic at full precision. *)
PROGRAM main
  VAR_INPUT
    a : LREAL;
    b : LREAL;
  END_VAR
  VAR_OUTPUT
    sum  : LREAL;
    quot : LREAL;
    prod : LREAL;
    sq   : LREAL;
    big  : LREAL;
  END_VAR
  sum  := a + b;
  quot := a / b;
  prod := a * b;
  sq   := SQRT(a);
  big  := 1.0E15 + 1.0;
END_PROGRAM
