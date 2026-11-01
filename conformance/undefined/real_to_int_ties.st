(* REAL_TO_INT and LREAL_TO_DINT on values exactly halfway between two
   integers. *)
PROGRAM main
  VAR_INPUT
    x : REAL;
    l : LREAL;
  END_VAR
  VAR_OUTPUT
    i : INT;
    d : DINT;
  END_VAR
  i := REAL_TO_INT(x);
  d := LREAL_TO_DINT(l);
END_PROGRAM
