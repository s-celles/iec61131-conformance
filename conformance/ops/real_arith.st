(* REAL arithmetic and real literals. *)
PROGRAM main
  VAR_INPUT
    x : REAL;
    y : REAL;
  END_VAR
  VAR_OUTPUT
    sum  : REAL;
    diff : REAL;
    prod : REAL;
    quot : REAL;
    neg  : REAL;
    lit1 : REAL;
    lit2 : REAL;
    lit3 : REAL;
  END_VAR
  sum  := x + y;
  diff := x - y;
  prod := x * y;
  quot := x / y;
  neg  := -x;
  lit1 := 1.0E3;
  lit2 := REAL#1.5;
  lit3 := -2.5E-2;
END_PROGRAM
