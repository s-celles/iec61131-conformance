(* TRUNC rounds toward zero (ed.3 table 22 rows 7 and 8, ed.2 table 22
   row 6), unlike REAL_TO_INT which rounds to nearest
   (ops/real_conversions). *)
PROGRAM main
  VAR_INPUT
    r : REAL;
  END_VAR
  VAR_OUTPUT
    t : DINT;
  END_VAR
  t := TRUNC(r);
END_PROGRAM
