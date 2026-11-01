(* FOR with a positive step and EXIT, plus a FOR with a negative step.
   All accumulators are recomputed from scratch every cycle. *)
PROGRAM main
  VAR_INPUT
    n : INT;
  END_VAR
  VAR_OUTPUT
    sum   : DINT;
    last  : INT;
    count : INT;
    down_count : INT;
    down_sum   : INT;
  END_VAR
  VAR
    i : INT;
    j : INT;
  END_VAR
  sum := 0;
  last := 0;
  count := 0;
  FOR i := 1 TO n BY 1 DO
    IF i > 5 THEN
      EXIT;
    END_IF;
    sum := sum + INT_TO_DINT(i);
    last := i;
    count := count + 1;
  END_FOR;

  down_count := 0;
  down_sum := 0;
  FOR j := 10 TO 1 BY -3 DO
    down_count := down_count + 1;
    down_sum := down_sum + j;
  END_FOR;
END_PROGRAM
