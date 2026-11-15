(* FIND yields an INT, including when embedded in signed arithmetic. *)
PROGRAM main
  VAR_INPUT
    i0 : INT;
  END_VAR
  VAR_OUTPUT
    m : INT;
    n : INT;
    c : BOOL;
    d : INT;
    absent : INT;
  END_VAR
  VAR
    src : STRING := 'abc';
    part : STRING := 'bc';
    missing : STRING := 'zz';
  END_VAR
  m := MAX(FIND(src, part), i0);
  n := MIN(FIND(src, part), i0);
  c := FIND(src, part) > i0;
  d := FIND(src, part) - 5;
  absent := FIND(src, missing);
END_PROGRAM
