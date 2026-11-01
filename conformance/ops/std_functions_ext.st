(* Extensible standard functions with three arguments, and standard
   functions called with formal (named) arguments. *)
PROGRAM main
  VAR_INPUT
    a   : INT;
    b   : INT;
    c   : INT;
    g : BOOL;
  END_VAR
  VAR_OUTPUT
    max3 : INT;
    min3 : INT;
    add3 : INT;
    mul3 : INT;
    lim  : INT;
    selv : INT;
  END_VAR
  max3 := MAX(a, b, c);
  min3 := MIN(a, b, c);
  add3 := ADD(a, b, c);
  mul3 := MUL(a, b, c);
  lim  := LIMIT(MN := b, IN := a, MX := c);
  selv := SEL(G := g, IN0 := a, IN1 := b);
END_PROGRAM
