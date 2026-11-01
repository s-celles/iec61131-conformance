(* An array of structures with a structure initialiser per element, member
   access through an index, an element modified in place and retained from
   cycle to cycle, and a copy of an element that does not alias it. *)
TYPE
  POINT : STRUCT
    x : INT;
    y : INT;
  END_STRUCT;
END_TYPE

PROGRAM main
  VAR_INPUT
    k : INT;   (* added to pts[2].x each cycle *)
  END_VAR
  VAR_OUTPUT
    sum_x  : INT;
    sum_y  : INT;
    px     : INT;   (* pts[2].x *)
    copy_y : INT;   (* pts[3].y after a copy of pts[3] was modified *)
  END_VAR
  VAR
    pts : ARRAY[1..3] OF POINT := [(x := 1, y := 10), (x := 2, y := 20), (x := 3, y := 30)];
    c   : POINT;
    i   : INT;
  END_VAR
  pts[2].x := pts[2].x + k;
  sum_x := 0;
  sum_y := 0;
  FOR i := 1 TO 3 DO
    sum_x := sum_x + pts[i].x;
    sum_y := sum_y + pts[i].y;
  END_FOR;
  px := pts[2].x;
  c := pts[3];
  c.y := c.y + 1;        (* c is a copy: pts[3] is unchanged *)
  copy_y := pts[3].y;
END_PROGRAM
