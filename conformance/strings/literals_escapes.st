(* STRING literals and the $ escape sequences. *)
PROGRAM main
  VAR_OUTPUT
    s1 : STRING;
    s2 : STRING;
    s3 : STRING;
    s4 : STRING;
    s5 : STRING;
    s6 : STRING;
    s7 : STRING;
    s8 : STRING;
    n1 : INT;
  END_VAR
  s1 := 'abc';
  s2 := '';
  s3 := 'it$'s';
  s4 := '$$';
  s5 := 'a b';
  s6 := 'tab$Tx';
  s7 := 'nl$Ny';
  s8 := '$41$42';
  n1 := LEN(s1);
END_PROGRAM
