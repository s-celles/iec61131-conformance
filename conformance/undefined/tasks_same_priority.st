(* Two tasks with the same interval and the same priority, due at the same
   instants; which runs first? Each program appends its digit to the marks. *)
PROGRAM mark_a
  VAR_EXTERNAL
    marks : DINT;
  END_VAR
  marks := marks * 10 + 1;
END_PROGRAM

PROGRAM mark_b
  VAR_EXTERNAL
    marks : DINT;
  END_VAR
  marks := marks * 10 + 2;
END_PROGRAM

CONFIGURATION conf
  VAR_GLOBAL
    marks : DINT;
  END_VAR
  RESOURCE res0 ON PLC
    TASK t_a(INTERVAL := T#100ms, PRIORITY := 0);
    TASK t_b(INTERVAL := T#100ms, PRIORITY := 0);
    PROGRAM p_a WITH t_a : mark_a;
    PROGRAM p_b WITH t_b : mark_b;
  END_RESOURCE
END_CONFIGURATION
