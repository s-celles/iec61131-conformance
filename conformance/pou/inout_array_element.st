(* An array element as the VAR_IN_OUT argument of a function, with a
   variable and a literal subscript and a lower bound of 1. *)
FUNCTION BUMP : INT
  VAR_IN_OUT
    n : INT;
  END_VAR
  VAR_INPUT
    d : INT;
  END_VAR
  n := n + d;
  BUMP := n;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    i : INT;    (* 1..3 *)
  END_VAR
  VAR_OUTPUT
    r : INT;
    s : INT;
    e1 : INT;
    e2 : INT;
    e3 : INT;
  END_VAR
  VAR
    arr : ARRAY[1..3] OF INT;
  END_VAR
  r := BUMP(arr[i], 5);
  s := BUMP(n := arr[3], d := 1);
  e1 := arr[1];
  e2 := arr[2];
  e3 := arr[3];
END_PROGRAM
