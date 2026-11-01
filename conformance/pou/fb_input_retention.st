(* A function block input that is not passed on a call keeps the value it
   received on an earlier call. The program selects, per cycle, which of
   the two inputs it passes. *)
FUNCTION_BLOCK ACC
  VAR_INPUT
    inc    : INT;
    enable : BOOL;
  END_VAR
  VAR_OUTPUT
    total : INT;
  END_VAR
  IF enable THEN
    total := total + inc;
  END_IF;
END_FUNCTION_BLOCK

PROGRAM main
  VAR_INPUT
    new_inc    : INT;
    set_inc    : BOOL;
    new_enable : BOOL;
    set_enable : BOOL;
  END_VAR
  VAR_OUTPUT
    total : INT;
  END_VAR
  VAR
    a : ACC;
  END_VAR
  IF set_inc AND set_enable THEN
    a(inc := new_inc, enable := new_enable);
  ELSIF set_inc THEN
    a(inc := new_inc);
  ELSIF set_enable THEN
    a(enable := new_enable);
  ELSE
    a();
  END_IF;
  total := a.total;
END_PROGRAM
