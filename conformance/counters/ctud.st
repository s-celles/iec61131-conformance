(* CTUD up-down counter, PV fixed at 2. *)
PROGRAM main
  VAR_INPUT
    cu : BOOL;
    cd : BOOL;
    r  : BOOL;
    ld : BOOL;
  END_VAR
  VAR_OUTPUT
    qu : BOOL;
    qd : BOOL;
    cv : INT;
  END_VAR
  VAR
    counter : CTUD;
  END_VAR
  counter(CU := cu, CD := cd, R := r, LD := ld, PV := 2);
  qu := counter.QU;
  qd := counter.QD;
  cv := counter.CV;
END_PROGRAM
