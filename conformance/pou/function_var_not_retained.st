(* A FUNCTION's VAR section is not retained between invocations: n starts
   from its initial value (0) on every call, so the result depends on this
   call's argument only. *)
FUNCTION BUMP : INT
  VAR_INPUT
    x : INT;
  END_VAR
  VAR
    n : INT;
  END_VAR
  n := n + x;
  BUMP := n;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    f : INT;
  END_VAR
  f := BUMP(x);
END_PROGRAM
