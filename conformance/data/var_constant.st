(* VAR CONSTANT: a constant keeps its declared value and can be used in
   expressions and as a FOR bound (ed.2 2.4.3, the CONSTANT qualifier;
   ed.3 to locate; not checked against the text, see
   notes/verification.md V-08). *)
PROGRAM main
  VAR_INPUT
    x : DINT;
  END_VAR
  VAR_OUTPUT
    sum : INT;
    scaled : DINT;
    limit_hit : BOOL;
    period : TIME;
  END_VAR
  VAR CONSTANT
    N : INT := 4;
    SCALE : DINT := 1000;
    THRESHOLD : DINT := 2000;
    CYCLE_TIME : TIME := T#2s;
  END_VAR
  VAR
    i : INT;
  END_VAR
  sum := 0;
  FOR i := 1 TO N DO
    sum := sum + i;
  END_FOR;
  scaled := x * SCALE;
  limit_hit := scaled >= THRESHOLD;
  period := CYCLE_TIME;
END_PROGRAM
