(* Comparison of character strings. *)
PROGRAM main
  VAR_OUTPUT
    e1 : BOOL;
    e2 : BOOL;
    l1 : BOOL;
    l2 : BOOL;
    l3 : BOOL;
    l4 : BOOL;
    g1 : BOOL;
    n1 : BOOL;
  END_VAR
  VAR
    a : STRING := 'abc';
    b : STRING := 'abd';
    c : STRING := 'ab';
    u : STRING := 'ABC';
    e : STRING := '';
  END_VAR
  e1 := a = 'abc';
  e2 := a = b;
  l1 := a < b;
  l2 := c < a;
  l3 := 'B' < 'a';
  l4 := e < 'a';
  g1 := 'b' > a;
  n1 := a <> u;
END_PROGRAM
