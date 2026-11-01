(* TON whose PT input is changed while the timer is running. *)
PROGRAM main
  VAR_INPUT
    in : BOOL;
    pt : TIME;
  END_VAR
  VAR_OUTPUT
    q  : BOOL;
    et : TIME;
  END_VAR
  VAR
    timer : TON;
  END_VAR
  timer(IN := in, PT := pt);
  q  := timer.Q;
  et := timer.ET;
END_PROGRAM
