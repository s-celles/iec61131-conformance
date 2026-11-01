(* Standard numeric and selection functions on INT and DINT, two-argument
   forms and positional arguments only. *)
PROGRAM main
  VAR_INPUT
    a   : INT;
    b   : INT;
    c   : INT;
    k   : INT;
    g : BOOL;
    da  : DINT;
    db  : DINT;
  END_VAR
  VAR_OUTPUT
    o_abs   : INT;
    o_min   : INT;
    o_max   : INT;
    o_limit : INT;
    o_sel   : INT;
    o_mux   : INT;
    d_abs   : DINT;
    d_min   : DINT;
  END_VAR
  o_abs   := ABS(a);
  o_min   := MIN(a, b);
  o_max   := MAX(a, b);
  o_limit := LIMIT(b, a, c);     (* MN := b, IN := a, MX := c *)
  o_sel   := SEL(g, a, b);     (* G := g, IN0 := a, IN1 := b *)
  o_mux   := MUX(k, a, b, c);    (* K := k, IN0 := a, IN1 := b, IN2 := c *)
  d_abs   := ABS(da);
  d_min   := MIN(da, db);
END_PROGRAM
