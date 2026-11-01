(* CONTINUE (ed.3 7.3.3.4.2 table 72, new in ed.3) skips the rest of the
   current iteration of the innermost FOR, WHILE or REPEAT loop and goes on
   with the next one. *)
PROGRAM main
  VAR_INPUT
    n : INT;
  END_VAR
  VAR_OUTPUT
    odd_sum : INT;   (* sum of the odd numbers 1..n *)
    w_count : INT;   (* n iterations of a WHILE, one skipped *)
    inner   : INT;   (* CONTINUE in a nested loop affects the inner one only *)
  END_VAR
  VAR
    i : INT;
    j : INT;
    k : INT;
  END_VAR
  odd_sum := 0;
  FOR i := 1 TO n DO
    IF i MOD 2 = 0 THEN
      CONTINUE;
    END_IF;
    odd_sum := odd_sum + i;
  END_FOR;

  w_count := 0;
  k := 0;
  WHILE k < n DO
    k := k + 1;
    IF k = 2 THEN
      CONTINUE;
    END_IF;
    w_count := w_count + 1;
  END_WHILE;

  inner := 0;
  FOR i := 1 TO 3 DO
    FOR j := 1 TO 3 DO
      IF j = 2 THEN
        CONTINUE;
      END_IF;
      inner := inner + 1;
    END_FOR;
  END_FOR;
END_PROGRAM
