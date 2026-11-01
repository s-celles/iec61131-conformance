(* Operand evaluation order observed through a function with a side effect
   on a VAR_IN_OUT argument. BUMP increments its argument and returns the
   new value. If the left operand of "-" is evaluated first:
   y = 1 - 10*2 = -19; if the right operand is evaluated first:
   y = 2 - 10*1 = -8. *)
FUNCTION BUMP : INT
  VAR_IN_OUT
    c : INT;
  END_VAR
  c := c + 1;
  BUMP := c;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    reset : BOOL;
  END_VAR
  VAR_OUTPUT
    y : INT;
    c : INT;
  END_VAR
  IF reset THEN
    c := 0;
  END_IF;
  y := BUMP(c) - 10 * BUMP(c);
END_PROGRAM
