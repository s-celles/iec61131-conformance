(* LEN used with negative INT values: MAX, MIN, comparison, subtraction. *)
PROGRAM main
  VAR_INPUT
    i0 : INT;
  END_VAR
  VAR_OUTPUT
    m : INT;
    n : INT;
    c : BOOL;
    d : INT;
  END_VAR
  VAR
    s : STRING := '';
    abc : STRING := 'abc';
  END_VAR
  m := MAX(LEN(s), i0);
  n := MIN(LEN(abc), i0);
  c := LEN(s) > i0;
  d := LEN(abc) - 5;
END_PROGRAM
