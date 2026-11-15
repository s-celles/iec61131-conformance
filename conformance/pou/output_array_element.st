(* An array element as the target of a function's VAR_OUTPUT (m => arr[i]),
   with a variable and a literal subscript and a lower bound of 1. *)
FUNCTION DIVMOD : INT
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    m : INT;
  END_VAR
  DIVMOD := a / b;
  m := a MOD b;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    i : INT;    (* 1..3 *)
    x : INT;
  END_VAR
  VAR_OUTPUT
    q : INT;
    q2 : INT;
    e1 : INT;
    e2 : INT;
    e3 : INT;
  END_VAR
  VAR
    arr : ARRAY[1..3] OF INT;
  END_VAR
  q := DIVMOD(a := x, b := 4, m => arr[i]);
  q2 := DIVMOD(a := x + 1, b := 4, m => arr[3]);
  e1 := arr[1];
  e2 := arr[2];
  e3 := arr[3];
END_PROGRAM
