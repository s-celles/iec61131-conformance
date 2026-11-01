(* Conversions between integer and real types, with values that are exact
   in the target type and real-to-integer values that are not ties. *)
PROGRAM main
  VAR_INPUT
    i : INT;
    d : DINT;
    u : UINT;
    x : REAL;    (* exactly representable, fractional part not .5 *)
    l : LREAL;   (* exactly representable in REAL too *)
  END_VAR
  VAR_OUTPUT
    i2r : REAL;
    d2l : LREAL;
    u2r : REAL;
    r2i : INT;
    r2l : LREAL;
    l2r : REAL;
    l2d : DINT;
  END_VAR
  i2r := INT_TO_REAL(i);
  d2l := DINT_TO_LREAL(d);
  u2r := UINT_TO_REAL(u);
  r2i := REAL_TO_INT(x);
  r2l := REAL_TO_LREAL(x);
  l2r := LREAL_TO_REAL(l);
  l2d := LREAL_TO_DINT(l);
END_PROGRAM
