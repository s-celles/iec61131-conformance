(* Two tasks due at the same instants: the one with the higher priority
   (lower number) runs first. The reader is declared before the writer so
   that declaration order and priority order disagree. *)
PROGRAM reader
  VAR_EXTERNAL
    g : INT;
  END_VAR
  VAR_OUTPUT
    seen : INT;
  END_VAR
  seen := g;
END_PROGRAM

PROGRAM writer
  VAR_EXTERNAL
    g : INT;
  END_VAR
  g := g + 10;
END_PROGRAM

CONFIGURATION conf
  VAR_GLOBAL
    g : INT;
  END_VAR
  RESOURCE res0 ON PLC
    TASK t_reader(INTERVAL := T#100ms, PRIORITY := 1);
    TASK t_writer(INTERVAL := T#100ms, PRIORITY := 0);
    PROGRAM p_reader WITH t_reader : reader;
    PROGRAM p_writer WITH t_writer : writer;
  END_RESOURCE
END_CONFIGURATION
