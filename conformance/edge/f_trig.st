(* F_TRIG falling-edge detector. *)
PROGRAM main
  VAR_INPUT
    clk : BOOL;
  END_VAR
  VAR_OUTPUT
    q : BOOL;
  END_VAR
  VAR
    edge : F_TRIG;
  END_VAR
  edge(CLK := clk);
  q := edge.Q;
END_PROGRAM
