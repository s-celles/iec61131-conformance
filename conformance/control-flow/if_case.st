(* IF / ELSIF / ELSE and CASE with single values, lists and ranges. *)
PROGRAM main
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    sign : INT;
    bucket : INT;
  END_VAR
  IF x < 0 THEN
    sign := -1;
  ELSIF x = 0 THEN
    sign := 0;
  ELSE
    sign := 1;
  END_IF;

  CASE x OF
    1:      bucket := 10;
    2, 3:   bucket := 20;
    4..6:   bucket := 30;
    -1:     bucket := -10;
  ELSE
    bucket := 0;
  END_CASE;
END_PROGRAM
