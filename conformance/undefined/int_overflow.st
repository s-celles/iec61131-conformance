(* INT addition whose mathematical result does not fit in INT. *)
PROGRAM main
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    s : INT;
    d : INT;
  END_VAR
  s := a + b;
  d := a - b;
END_PROGRAM
