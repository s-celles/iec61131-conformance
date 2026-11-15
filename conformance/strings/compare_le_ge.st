(* <= and >= between two STRING variables. *)
PROGRAM main
  VAR_OUTPUT
    le1 : BOOL;
    le2 : BOOL;
    le3 : BOOL;
    ge1 : BOOL;
    ge2 : BOOL;
    ge3 : BOOL;
  END_VAR
  VAR
    a : STRING := 'abc';
    b : STRING := 'abd';
    c : STRING := 'ab';
    d : STRING := 'abc';
  END_VAR
  le1 := a <= b;
  le2 := a <= d;
  le3 := a <= c;
  ge1 := a >= b;
  ge2 := a >= d;
  ge3 := a >= c;
END_PROGRAM
