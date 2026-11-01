(* Declared initial values of a function block's inputs, outputs and
   internal variables apply to each instance. The instance is only ever
   called with no arguments. *)
FUNCTION_BLOCK ACC
  VAR_INPUT
    inc    : INT  := 1;
    enable : BOOL := TRUE;
  END_VAR
  VAR_OUTPUT
    total     : INT := 10;
    untouched : INT := 7;
  END_VAR
  VAR
    calls : INT := 100;
  END_VAR
  calls := calls + 1;
  IF enable THEN
    total := total + inc;
  END_IF;
END_FUNCTION_BLOCK

PROGRAM main
  VAR_OUTPUT
    total     : INT;
    untouched : INT;
    base      : INT := 5;
  END_VAR
  VAR
    a : ACC;
  END_VAR
  a();
  total     := a.total;
  untouched := a.untouched;
  base      := base + 1;
END_PROGRAM
