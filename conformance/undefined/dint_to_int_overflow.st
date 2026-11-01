(* Conversions whose source value is out of the target type's range. *)
PROGRAM main
  VAR_INPUT
    d : DINT;
    i : INT;
    u : UINT;
  END_VAR
  VAR_OUTPUT
    d2i : INT;
    d2u : UINT;
    i2u : UINT;
    u2i : INT;
  END_VAR
  d2i := DINT_TO_INT(d);
  d2u := DINT_TO_UINT(d);
  i2u := INT_TO_UINT(i);
  u2i := UINT_TO_INT(u);
END_PROGRAM
