(* TOF off-delay timer: PT fixed at 200 ms. *)
PROGRAM main
  VAR_INPUT
    in : BOOL;
  END_VAR
  VAR_OUTPUT
    q  : BOOL;
    et : TIME;
  END_VAR
  VAR
    timer : TOF;
  END_VAR
  timer(IN := in, PT := T#200ms);
  q  := timer.Q;
  et := timer.ET;
END_PROGRAM
