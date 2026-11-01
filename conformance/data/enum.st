(* An enumerated type: default initial value, assignment, comparison and
   CASE on an enumerated selector. *)
TYPE
  COLOR : (RED, GREEN, BLUE);
END_TYPE

PROGRAM main
  VAR_INPUT
    pick : INT;    (* 0, 1, 2 select a colour; anything else leaves it *)
  END_VAR
  VAR_OUTPUT
    code     : INT;
    is_green : BOOL;
    same     : BOOL;
  END_VAR
  VAR
    c    : COLOR;
    prev : COLOR;
  END_VAR
  prev := c;
  CASE pick OF
    0: c := RED;
    1: c := GREEN;
    2: c := BLUE;
  END_CASE;
  CASE c OF
    RED:   code := 1;
    GREEN: code := 2;
    BLUE:  code := 3;
  END_CASE;
  is_green := c = GREEN;
  same := c = prev;
END_PROGRAM
