(* CASE on an expression, with negative values, lists, subranges, several
   statements in one branch, and ELSE. *)
PROGRAM main
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    branch : INT;
    neg    : BOOL;
    cnt    : INT;
  END_VAR
  CASE x MOD 4 OF
    0:      branch := 10;
    1, -1:  branch := 11;
    2, -2:  branch := 12;
  ELSE
    branch := 13;         (* 3 and -3 *)
  END_CASE;

  CASE x OF
    -10..-1:
      neg := TRUE;
      cnt := cnt + 1;
    0:
      neg := FALSE;
      cnt := cnt + 1;
  ELSE
    neg := FALSE;
  END_CASE;
END_PROGRAM
