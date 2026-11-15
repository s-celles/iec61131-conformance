(* Selection functions accept STRING as an elementary, ordered type. *)
PROGRAM main
  VAR_OUTPUT
    lo : STRING;
    hi : STRING;
    at_low : STRING;
    within : STRING;
    at_high : STRING;
  END_VAR
  VAR
    a : STRING := 'abc';
    b : STRING := 'abd';
    c : STRING := 'abe';
  END_VAR
  lo := MIN(a, b);
  hi := MAX(a, b);
  at_low := LIMIT(b, a, c);
  within := LIMIT(a, b, c);
  at_high := LIMIT(a, c, b);
END_PROGRAM
