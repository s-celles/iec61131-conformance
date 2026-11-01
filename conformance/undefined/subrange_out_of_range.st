(* Assigning a value outside the limits of a subrange type: the standard
   defines the limits (ed.3 6.4.4.4.3 / ed.2 2.3.3.1) but not what happens
   when they are violated; an implementation may refuse to compile, stop
   the cycle (error), clamp, or store the value unchecked. *)
TYPE
  SMALL : INT (5..10);
END_TYPE

PROGRAM main
  VAR_INPUT
    v : INT;
  END_VAR
  VAR_OUTPUT
    s : INT;
  END_VAR
  VAR
    sm : SMALL;
  END_VAR
  sm := v;
  s := sm;
END_PROGRAM
