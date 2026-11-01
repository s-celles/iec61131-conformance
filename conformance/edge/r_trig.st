(* R_TRIG rising-edge detector. *)
PROGRAM main
  VAR_INPUT
    clk : BOOL;
  END_VAR
  VAR_OUTPUT
    q : BOOL;
  END_VAR
  VAR
    edge : R_TRIG;
  END_VAR
  edge(CLK := clk);
  q := edge.Q;
END_PROGRAM
