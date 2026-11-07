(* Formal calls of standard functions with the arguments in another order
   than the declaration. *)
PROGRAM main
  VAR_INPUT
    i0 : INT;
    g : BOOL;
  END_VAR
  VAR_OUTPUT
    l1 : INT;
    l2 : INT;
    s1 : INT;
    m1 : INT;
    x1 : INT;
  END_VAR
  l1 := LIMIT(MN := 0, IN := i0, MX := 10);
  l2 := LIMIT(MX := 10, IN := i0, MN := 0);
  s1 := SEL(IN1 := 20, G := g, IN0 := 10);
  m1 := MUX(IN1 := 200, IN0 := 100, K := 1, IN2 := 300);
  x1 := MUX(IN2 := 3, K := 2, IN0 := 1, IN1 := 2);
END_PROGRAM
