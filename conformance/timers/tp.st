(* TP pulse timer: PT fixed at 300 ms. *)
PROGRAM main
  VAR_INPUT
    in : BOOL;
  END_VAR
  VAR_OUTPUT
    q  : BOOL;
    et : TIME;
  END_VAR
  VAR
    timer : TP;
  END_VAR
  timer(IN := in, PT := T#300ms);
  q  := timer.Q;
  et := timer.ET;
END_PROGRAM
