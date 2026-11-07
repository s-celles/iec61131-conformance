(* A call to a function with a VAR_IN_OUT or a VAR_OUTPUT, as an argument of
   standard functions and of another user function. *)
FUNCTION BUMP : INT
  VAR_IN_OUT
    n : INT;
  END_VAR
  n := n + 1;
  BUMP := n;
END_FUNCTION

FUNCTION SPLIT : INT
  VAR_INPUT
    a : INT;
  END_VAR
  VAR_OUTPUT
    r : INT;
  END_VAR
  SPLIT := a / 10;
  r := a MOD 10;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    i0 : INT;
  END_VAR
  VAR_OUTPUT
    a : INT;
    m : INT;
    s : INT;
    x : INT;
    q : INT;
    r : INT;
    calls : INT;
  END_VAR
  VAR
    one : INT := 1;
    zero : INT := 0;
    yes : BOOL := TRUE;
  END_VAR
  a := ABS(BUMP(calls) - 10);
  m := MIN(i0, BUMP(calls));
  s := SEL(yes, zero, BUMP(calls));
  x := MUX(one, zero, SPLIT(a := i0, r => r));
  q := SPLIT(a := BUMP(calls) * 10 + 7, r => r);
END_PROGRAM
