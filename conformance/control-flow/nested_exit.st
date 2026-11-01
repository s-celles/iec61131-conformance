(* EXIT leaves the innermost enclosing loop only. *)
PROGRAM main
  VAR_INPUT
    n : INT;
  END_VAR
  VAR_OUTPUT
    outer : INT;
    inner : INT;
    w     : INT;
  END_VAR
  VAR
    i : INT;
    j : INT;
  END_VAR
  outer := 0;
  inner := 0;
  FOR i := 1 TO 3 DO
    FOR j := 1 TO 10 DO
      IF j > n THEN
        EXIT;             (* ends the FOR j loop; FOR i continues *)
      END_IF;
      inner := inner + 1;
    END_FOR;
    outer := outer + 1;
  END_FOR;

  w := 0;
  FOR i := 1 TO 2 DO
    WHILE TRUE DO
      w := w + 1;
      IF w MOD 3 = 0 THEN
        EXIT;             (* ends the WHILE; FOR i continues *)
      END_IF;
    END_WHILE;
  END_FOR;
END_PROGRAM
