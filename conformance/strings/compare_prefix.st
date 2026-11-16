(* = and <> between STRING variables where one is a prefix of the other.
   strings/compare tests a prefix only with <. Found by tools/fuzz
   (profile strings, OpenPLC's matiec). *)
PROGRAM main
  VAR_OUTPUT
    eq1 : BOOL;
    eq2 : BOOL;
    eq3 : BOOL;
    ne1 : BOOL;
    ne2 : BOOL;
    ne3 : BOOL;
  END_VAR
  VAR
    a : STRING := 'abc';
    c : STRING := 'ab';
    d : STRING := 'abc';
    e : STRING := '';
  END_VAR
  eq1 := c = a;
  eq2 := e = a;
  eq3 := a = d;
  ne1 := a <> c;
  ne2 := a <> e;
  ne3 := a <> d;
END_PROGRAM
