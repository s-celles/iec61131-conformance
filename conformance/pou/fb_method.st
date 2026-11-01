(* Methods of a function block (ed.3 6.6.3.5, table 48, new in ed.3): a
   METHOD has access to the instance's variables, takes inputs and returns
   a value; it is called as instance.method(...). *)
FUNCTION_BLOCK COUNTER
  VAR_OUTPUT
    cv : INT;
  END_VAR
  VAR
    bodies : INT;   (* times the FB body itself ran: never, here *)
  END_VAR
  METHOD BUMP : INT
    VAR_INPUT
      n : INT;
    END_VAR
    cv := cv + n;
    BUMP := cv;
  END_METHOD
  METHOD CLEAR : BOOL
    cv := 0;
    CLEAR := TRUE;
  END_METHOD
  bodies := bodies + 1;
END_FUNCTION_BLOCK

PROGRAM main
  VAR_INPUT
    n   : INT;
    rst : BOOL;
  END_VAR
  VAR_OUTPUT
    ret : INT;   (* value returned by BUMP *)
    cv  : INT;   (* the instance's output *)
  END_VAR
  VAR
    c : COUNTER;
  END_VAR
  IF rst THEN
    c.CLEAR();
  END_IF;
  ret := c.BUMP(n := n);
  cv  := c.cv;
END_PROGRAM
