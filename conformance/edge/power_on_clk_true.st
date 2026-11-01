(* R_TRIG and F_TRIG whose CLK is already TRUE on the first evaluation. *)
PROGRAM main
  VAR_INPUT
    clk : BOOL;
  END_VAR
  VAR_OUTPUT
    qr : BOOL;
    qf : BOOL;
  END_VAR
  VAR
    rt : R_TRIG;
    ft : F_TRIG;
  END_VAR
  rt(CLK := clk);
  ft(CLK := clk);
  qr := rt.Q;
  qf := ft.Q;
END_PROGRAM
