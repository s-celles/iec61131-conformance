(* FOR loop whose final value is modified by the loop body. A guard on
   count bounds the loop whatever the runtime does. *)
PROGRAM main
  VAR_INPUT
    start_n : INT;
  END_VAR
  VAR_OUTPUT
    count : INT;
    n_after : INT;
  END_VAR
  VAR
    i : INT;
    n : INT;
  END_VAR
  n := start_n;
  count := 0;
  FOR i := 1 TO n DO
    n := n + 1;
    count := count + 1;
    IF count >= 50 THEN
      EXIT;
    END_IF;
  END_FOR;
  n_after := n;
END_PROGRAM
