(* TON on-delay timer: PT fixed at 300 ms, IN driven from outside, Q and ET
   exposed as program variables. *)
PROGRAM main
  VAR_INPUT
    in : BOOL;
  END_VAR
  VAR_OUTPUT
    q  : BOOL;
    et : TIME;
  END_VAR
  VAR
    timer : TON;
  END_VAR
  timer(IN := in, PT := T#300ms);
  q  := timer.Q;
  et := timer.ET;
END_PROGRAM
