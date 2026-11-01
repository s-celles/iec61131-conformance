(* WHILE and REPEAT loops recomputed every cycle. *)
PROGRAM main
  VAR_INPUT
    n : UINT;
  END_VAR
  VAR_OUTPUT
    iters : UINT;
    acc   : DINT;
    rep   : UINT;
  END_VAR
  VAR
    k : UINT;
  END_VAR
  k := 0;
  acc := 0;
  WHILE k < n DO
    k := k + 1;
    acc := acc + UINT_TO_DINT(k);
  END_WHILE;
  iters := k;

  (* REPEAT tests its condition after the body: at least one pass. *)
  rep := 0;
  REPEAT
    rep := rep + 1;
  UNTIL rep >= n
  END_REPEAT;
END_PROGRAM
