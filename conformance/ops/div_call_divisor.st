(* The divisor of / and MOD is a call to a function with a VAR_IN_OUT: the
   call is made once per occurrence. Found in the review of beremiz/matiec#47. *)
FUNCTION BUMP : INT
  VAR_IN_OUT
    n : INT;
  END_VAR
  n := n + 1;
  BUMP := 2;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    a : INT;
  END_VAR
  VAR_OUTPUT
    q : INT;
    m : INT;
    calls : INT;
  END_VAR
  q := a / BUMP(calls);
  m := a MOD BUMP(calls);
END_PROGRAM
