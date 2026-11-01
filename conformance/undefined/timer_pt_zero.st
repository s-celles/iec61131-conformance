(* TON, TOF and TP with PT = T#0ms. *)
PROGRAM main
  VAR_INPUT
    in : BOOL;
  END_VAR
  VAR_OUTPUT
    q_ton  : BOOL;
    et_ton : TIME;
    q_tof  : BOOL;
    et_tof : TIME;
    q_tp   : BOOL;
    et_tp  : TIME;
  END_VAR
  VAR
    t_on : TON;
    t_of : TOF;
    t_p  : TP;
  END_VAR
  t_on(IN := in, PT := T#0ms);
  t_of(IN := in, PT := T#0ms);
  t_p(IN := in, PT := T#0ms);
  q_ton  := t_on.Q;
  et_ton := t_on.ET;
  q_tof  := t_of.Q;
  et_tof := t_of.ET;
  q_tp   := t_p.Q;
  et_tp  := t_p.ET;
END_PROGRAM
