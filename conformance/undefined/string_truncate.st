(* A value longer than the declared length of a STRING[n]. *)
PROGRAM main
  VAR_OUTPUT
    s3 : STRING[3];
    n3 : INT;
    c2 : STRING[2];
    n2 : INT;
  END_VAR
  s3 := 'abcdef';
  n3 := LEN(s3);
  c2 := CONCAT('ab', 'cd');
  n2 := LEN(c2);
END_PROGRAM
