(* Two programs on two periodic tasks with different intervals. *)
PROGRAM fast
  VAR_EXTERNAL
    fast_n : INT;
  END_VAR
  fast_n := fast_n + 1;
END_PROGRAM

PROGRAM slow
  VAR_EXTERNAL
    slow_n : INT;
  END_VAR
  slow_n := slow_n + 1;
END_PROGRAM

CONFIGURATION conf
  VAR_GLOBAL
    fast_n : INT;
    slow_n : INT;
  END_VAR
  RESOURCE res0 ON PLC
    TASK t_fast(INTERVAL := T#100ms, PRIORITY := 1);
    TASK t_slow(INTERVAL := T#300ms, PRIORITY := 2);
    PROGRAM p_fast WITH t_fast : fast;
    PROGRAM p_slow WITH t_slow : slow;
  END_RESOURCE
END_CONFIGURATION
