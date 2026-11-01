(* String variables across cycles: accumulation with CONCAT, an initial
   value, and assignment as a copy. *)
PROGRAM main
  VAR_INPUT
    push : BOOL;
  END_VAR
  VAR_OUTPUT
    acc  : STRING;
    n    : INT;
    copy : STRING;
  END_VAR
  VAR
    src : STRING := 'ab';
  END_VAR
  IF push THEN
    acc := CONCAT(acc, 'x');
  END_IF;
  n := LEN(acc);
  copy := src;                  (* a copy: the next line does not change it *)
  src  := CONCAT(src, 'z');
END_PROGRAM
