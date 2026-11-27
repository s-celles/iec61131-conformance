(* Two enumerated types sharing value names: a value is written with its
   type name, Color#green and Light#green, wherever the name alone would
   be ambiguous, in assignments, comparisons and CASE labels (ed.3
   6.4.4.1, ed.2 2.3.3.1; not checked against the text, see
   notes/verification.md V-07). *)
TYPE
  Color : (red, green, blue);
  Light : (off, red, green);
END_TYPE

PROGRAM main
  VAR_INPUT
    pick : INT;
  END_VAR
  VAR_OUTPUT
    ccode : INT;
    lcode : INT;
    is_green : BOOL;
  END_VAR
  VAR
    c : Color := Color#blue;
    l : Light := Light#green;
  END_VAR
  IF pick = 1 THEN
    c := Color#green;
    l := Light#red;
  ELSIF pick = 2 THEN
    c := Color#red;
    l := Light#off;
  END_IF;
  CASE c OF
    Color#red: ccode := 1;
    Color#green: ccode := 2;
    Color#blue: ccode := 3;
  END_CASE;
  CASE l OF
    Light#off: lcode := 0;
    Light#red: lcode := 1;
    Light#green: lcode := 2;
  END_CASE;
  is_green := c = Color#green;
END_PROGRAM
