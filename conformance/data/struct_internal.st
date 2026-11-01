(* Structures inside the program: member access, whole-structure
   assignment (a copy), and a nested structure. *)
TYPE
  POINT : STRUCT
    x : INT;
    y : INT;
  END_STRUCT;
  RECT : STRUCT
    tl : POINT;
    br : POINT;
  END_STRUCT;
END_TYPE

PROGRAM main
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    qx   : INT;
    qy   : INT;
    px   : INT;
    area : INT;
  END_VAR
  VAR
    p : POINT;
    q : POINT;
    r : RECT;
  END_VAR
  p.x := a;
  p.y := b;
  q := p;          (* copies the value: q is independent of p afterwards *)
  p.x := 0;
  qx := q.x;
  qy := q.y;
  px := p.x;
  r.tl := q;
  r.br.x := q.x + a;
  r.br.y := q.y + b;
  area := (r.br.x - r.tl.x) * (r.br.y - r.tl.y);
END_PROGRAM
