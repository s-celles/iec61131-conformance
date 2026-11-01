(* Value of a FOR control variable after the loop has terminated. *)
PROGRAM main
  VAR_INPUT
    n : INT;
  END_VAR
  VAR_OUTPUT
    i_after : INT;
    sum     : INT;
  END_VAR
  VAR
    i : INT;
  END_VAR
  sum := 0;
  FOR i := 1 TO n DO
    sum := sum + i;
  END_FOR;
  i_after := i;
END_PROGRAM
