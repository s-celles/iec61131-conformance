(* One-dimensional arrays inside the program, one with a negative lower
   bound; the harness sees scalars only. *)
PROGRAM main
  VAR_INPUT
    idx : INT;    (* 0..4 *)
    val : INT;
  END_VAR
  VAR_OUTPUT
    sum    : INT;
    at_idx : INT;
    lo     : INT;
    hi     : INT;
  END_VAR
  VAR
    arr : ARRAY[0..4] OF INT;
    neg : ARRAY[-2..2] OF INT;
    i   : INT;
  END_VAR
  arr[idx] := val;
  sum := 0;
  FOR i := 0 TO 4 DO
    sum := sum + arr[i];
  END_FOR;
  at_idx := arr[idx];
  neg[idx - 2] := val;
  lo := neg[-2];
  hi := neg[2];
END_PROGRAM
