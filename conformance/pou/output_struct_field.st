(* A structure member as the target of a function's VAR_OUTPUT
   (m => p.y, m => pa[i].y). *)
TYPE
  PT : STRUCT
    x : INT;
    y : INT;
  END_STRUCT;
END_TYPE

FUNCTION DIVMOD : INT
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    m : INT;
  END_VAR
  DIVMOD := a / b;
  m := a MOD b;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    i : INT;    (* 1..3 *)
    x : INT;
  END_VAR
  VAR_OUTPUT
    q  : INT;
    q2 : INT;
    py : INT;
    e1 : INT;   (* pa[1].y *)
    e2 : INT;
    e3 : INT;
  END_VAR
  VAR
    p  : PT;
    pa : ARRAY[1..3] OF PT;
  END_VAR
  q := DIVMOD(a := x, b := 4, m => p.y);
  q2 := DIVMOD(a := x + 1, b := 4, m => pa[i].y);
  py := p.y;
  e1 := pa[1].y;
  e2 := pa[2].y;
  e3 := pa[3].y;
END_PROGRAM
