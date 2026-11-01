(* CTU up-counter, PV fixed at 3. *)
PROGRAM main
  VAR_INPUT
    cu : BOOL;
    r  : BOOL;
  END_VAR
  VAR_OUTPUT
    q  : BOOL;
    cv : INT;
  END_VAR
  VAR
    counter : CTU;
  END_VAR
  counter(CU := cu, R := r, PV := 3);
  q  := counter.Q;
  cv := counter.CV;
END_PROGRAM
