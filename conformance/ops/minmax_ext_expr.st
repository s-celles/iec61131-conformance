(* MIN/MAX with three INT inputs, an expression in each possible position. *)
PROGRAM main
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    max_first : INT;
    max_second : INT;
    max_last : INT;
    min_first : INT;
    min_second : INT;
    min_last : INT;
  END_VAR
  VAR
    c : INT := 2;
  END_VAR
  max_first := MAX(a * 2, b, c);
  max_second := MAX(b, a * 2, c);
  max_last := MAX(b, c, a * 2);
  min_first := MIN(a - 10, a, c);
  min_second := MIN(a, a - 10, c);
  min_last := MIN(a, c, a - 10);
END_PROGRAM
