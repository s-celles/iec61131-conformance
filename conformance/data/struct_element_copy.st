(* A structure assigned as a whole to an element of an array of structures
   and back, with a variable subscript. See struct_element_copy.trace. *)
TYPE
  POINT : STRUCT
    x : INT;
    y : INT;
  END_STRUCT;
END_TYPE

PROGRAM main
  VAR_INPUT
    i : INT;    (* 1..3 *)
    k : INT;
  END_VAR
  VAR_OUTPUT
    s1 : INT;   (* pts[1].x + pts[1].y *)
    s2 : INT;
    s3 : INT;
    cs : INT;   (* c.x + c.y *)
  END_VAR
  VAR
    pts : ARRAY[1..3] OF POINT;
    p   : POINT;
    c   : POINT;
  END_VAR
  p.x := k;
  p.y := 10 * i;
  pts[i] := p;       (* copies p into the element *)
  p.x := 0;          (* pts[i] is unchanged *)
  c := pts[i];       (* copies the element *)
  c.y := c.y + 1;    (* pts[i] is unchanged *)
  s1 := pts[1].x + pts[1].y;
  s2 := pts[2].x + pts[2].y;
  s3 := pts[3].x + pts[3].y;
  cs := c.x + c.y;
END_PROGRAM
