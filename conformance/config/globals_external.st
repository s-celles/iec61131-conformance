(* One program instance on one periodic task, exchanging data through
   VAR_GLOBAL / VAR_EXTERNAL; one global has an initial value. *)
PROGRAM counter
  VAR_EXTERNAL
    g_in  : INT;
    g_cnt : INT;
    g_sum : DINT;
  END_VAR
  VAR_OUTPUT
    n : INT;
  END_VAR
  n := n + 1;
  g_cnt := g_cnt + 1;
  g_sum := g_sum + INT_TO_DINT(g_in);
END_PROGRAM

CONFIGURATION conf
  VAR_GLOBAL
    g_in  : INT;
    g_cnt : INT;
    g_sum : DINT := 1000;
  END_VAR
  RESOURCE res0 ON PLC
    TASK t0(INTERVAL := T#100ms, PRIORITY := 0);
    PROGRAM p0 WITH t0 : counter;
  END_RESOURCE
END_CONFIGURATION
