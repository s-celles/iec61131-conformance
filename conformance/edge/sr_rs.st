(* SR (set dominant) and RS (reset dominant) bistables driven by the same
   two inputs. *)
PROGRAM main
  VAR_INPUT
    s : BOOL;
    r : BOOL;
  END_VAR
  VAR_OUTPUT
    q_sr : BOOL;
    q_rs : BOOL;
  END_VAR
  VAR
    latch_sr : SR;
    latch_rs : RS;
  END_VAR
  latch_sr(S1 := s, R := r);
  latch_rs(S := s, R1 := r);
  q_sr := latch_sr.Q1;
  q_rs := latch_rs.Q1;
END_PROGRAM
