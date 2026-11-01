(* CTD down-counter, PV fixed at 3. *)
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
  counter(CD := cd, LD := ld, PV := 3);
  q  := counter.Q;
  cv := counter.CV;
END_PROGRAM
