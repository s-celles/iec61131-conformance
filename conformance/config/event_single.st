(* A SINGLE (event-triggered) task next to a periodic one. *)
PROGRAM on_event
  VAR_EXTERNAL
    ev_n : INT;
  END_VAR
  ev_n := ev_n + 1;
END_PROGRAM

PROGRAM ticker
  VAR_EXTERNAL
    tick_n : INT;
  END_VAR
  tick_n := tick_n + 1;
END_PROGRAM

CONFIGURATION conf
  VAR_GLOBAL
    trig   : BOOL;
    ev_n   : INT;
    tick_n : INT;
  END_VAR
  RESOURCE res0 ON PLC
    TASK t_cyc(INTERVAL := T#100ms, PRIORITY := 1);
    TASK t_ev(SINGLE := trig, PRIORITY := 0);
    PROGRAM p_cyc WITH t_cyc : ticker;
    PROGRAM p_ev WITH t_ev : on_event;
  END_RESOURCE
END_CONFIGURATION
