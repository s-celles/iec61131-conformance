(* A slow producer and a fast consumer exchanging a value through a
   global: the consumer runs every step and sees each new value in the
   step the producer wrote it, since the producer has the higher
   priority. *)
PROGRAM producer
  VAR_EXTERNAL
    cmd : INT;
  END_VAR
  cmd := cmd + 1;
END_PROGRAM

PROGRAM consumer
  VAR_EXTERNAL
    cmd : INT;
  END_VAR
  VAR_OUTPUT
    ack     : INT;
    changes : INT;
  END_VAR
  IF cmd <> ack THEN
    changes := changes + 1;
  END_IF;
  ack := cmd;
END_PROGRAM

CONFIGURATION conf
  VAR_GLOBAL
    cmd : INT;
  END_VAR
  RESOURCE res0 ON PLC
    TASK t_prod(INTERVAL := T#200ms, PRIORITY := 0);
    TASK t_cons(INTERVAL := T#100ms, PRIORITY := 1);
    PROGRAM p_prod WITH t_prod : producer;
    PROGRAM p_cons WITH t_cons : consumer;
  END_RESOURCE
END_CONFIGURATION
