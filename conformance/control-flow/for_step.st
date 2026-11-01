(* FOR with a negative BY, a step that overshoots the final value, a range
   that is empty from the start, and a range given by inputs
   (ed.3 7.3.3.4.2 / ed.2 3.3.2.4: the body is executed while the control
   variable has not passed the final value in the direction of the step). *)
PROGRAM main
  VAR_INPUT
    lo : INT;
    hi : INT;
  END_VAR
  VAR_OUTPUT
    down_sum : INT;   (* 10 TO 1 BY -3: 10, 7, 4, 1 *)
    down_n   : INT;
    by4_sum  : INT;   (* 1 TO 10 BY 4: 1, 5, 9 *)
    by4_n    : INT;
    empty_n  : INT;   (* 5 TO 1: no iteration *)
    up_n     : INT;   (* lo TO hi *)
  END_VAR
  VAR
    i : INT;
  END_VAR
  down_sum := 0;
  down_n := 0;
  FOR i := 10 TO 1 BY -3 DO
    down_sum := down_sum + i;
    down_n := down_n + 1;
  END_FOR;

  by4_sum := 0;
  by4_n := 0;
  FOR i := 1 TO 10 BY 4 DO
    by4_sum := by4_sum + i;
    by4_n := by4_n + 1;
  END_FOR;

  empty_n := 0;
  FOR i := 5 TO 1 DO
    empty_n := empty_n + 1;
  END_FOR;

  up_n := 0;
  FOR i := lo TO hi DO
    up_n := up_n + 1;
  END_FOR;
END_PROGRAM
