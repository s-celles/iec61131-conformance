(* A structure member as the VAR_IN_OUT argument of a function: a member of
   a structured variable and a member of an array element. *)
TYPE
  PT : STRUCT
    x : INT;
    y : INT;
  END_STRUCT;
END_TYPE

FUNCTION BUMP : INT
  VAR_IN_OUT
    n : INT;
  END_VAR
  VAR_INPUT
    d : INT;
  END_VAR
  n := n + d;
  BUMP := n;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    i : INT;    (* 1..3 *)
  END_VAR
  VAR_OUTPUT
    r1 : INT;
    r2 : INT;
    px : INT;
    e1 : INT;   (* pa[1].x *)
    e2 : INT;
    e3 : INT;
  END_VAR
  VAR
    p  : PT;
    pa : ARRAY[1..3] OF PT;
  END_VAR
  r1 := BUMP(p.x, 5);
  r2 := BUMP(pa[i].x, 1);
  px := p.x;
  e1 := pa[1].x;
  e2 := pa[2].x;
  e3 := pa[3].x;
END_PROGRAM
