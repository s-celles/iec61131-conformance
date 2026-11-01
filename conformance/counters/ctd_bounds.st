(* CTD loaded with PV = -32768, the minimum of INT: counting down from
   there must not underflow. *)
PROGRAM main
  VAR_INPUT
    cd : BOOL;
    ld : BOOL;
  END_VAR
  VAR_OUTPUT
    q  : BOOL;
    cv : INT;
  END_VAR
  VAR
    counter : CTD;
  END_VAR
  counter(CD := cd, LD := ld, PV := -32768);
  q  := counter.Q;
  cv := counter.CV;
END_PROGRAM
