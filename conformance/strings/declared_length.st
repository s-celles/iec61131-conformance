(* STRING[n]: a declared maximum length, with and without an initial
   value, and a named string type. *)
TYPE
  S5 : STRING[5];
END_TYPE

PROGRAM main
  VAR_OUTPUT
    s3  : STRING[3];
    s4  : STRING[4] := 'init';
    s5  : S5;
    n3  : INT;
    n4  : INT;
    n5  : INT;
    cat : STRING[8];
  END_VAR
  s3  := 'xyz';
  s5  := 'abcde';
  n3  := LEN(s3);
  n4  := LEN(s4);
  n5  := LEN(s5);
  cat := CONCAT(s3, s4);
END_PROGRAM
