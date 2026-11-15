(* Extensible CONCAT, with STRING variables rather than literal arguments. *)
PROGRAM main
  VAR_OUTPUT
    joined3 : STRING;
    joined4 : STRING;
    nested : STRING;
  END_VAR
  VAR
    a : STRING := 'ab';
    b : STRING := 'CD';
    c : STRING := 'ef';
    d : STRING := 'GH';
  END_VAR
  joined3 := CONCAT(a, b, c);
  joined4 := CONCAT(a, b, c, d);
  nested := CONCAT(CONCAT(a, b), c);
END_PROGRAM
