(* User-defined functions called from a program: a function with three
   inputs and a local variable, and a function called with the result of
   another one. *)
FUNCTION CLAMP : INT
  VAR_INPUT
    v  : INT;
    lo : INT;
    hi : INT;
  END_VAR
  VAR
    tmp : INT;
  END_VAR
  tmp := v;
  IF tmp < lo THEN
    tmp := lo;
  END_IF;
  IF tmp > hi THEN
    tmp := hi;
  END_IF;
  CLAMP := tmp;
END_FUNCTION

FUNCTION DOUBLE_PLUS : DINT
  VAR_INPUT
    a : DINT;
    b : DINT;
  END_VAR
  DOUBLE_PLUS := 2 * a + b;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    x : INT;
    d : DINT;
  END_VAR
  VAR_OUTPUT
    y : INT;
    e : DINT;
  END_VAR
  y := CLAMP(x, -10, 10);
  e := DOUBLE_PLUS(INT_TO_DINT(CLAMP(x, 0, 100)), d);
END_PROGRAM
