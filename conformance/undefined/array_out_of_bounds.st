(* Reading an array element outside the declared subrange. *)
PROGRAM main
  VAR_INPUT
    idx : INT;
  END_VAR
  VAR_OUTPUT
    v  : INT;
    ok : BOOL;
  END_VAR
  VAR
    arr : ARRAY[0..3] OF INT;
    i   : INT;
  END_VAR
  FOR i := 0 TO 3 DO
    arr[i] := i * 10;
  END_FOR;
  ok := FALSE;
  v := arr[idx];
  ok := TRUE;
END_PROGRAM
