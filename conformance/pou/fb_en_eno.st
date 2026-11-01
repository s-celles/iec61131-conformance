(* The implicit EN input and ENO output of a function block: with EN FALSE
   the body is not executed and ENO is FALSE. *)
FUNCTION_BLOCK COUNT
  VAR_INPUT
    inc : INT;
  END_VAR
  VAR_OUTPUT
    total : INT;
  END_VAR
  total := total + inc;
END_FUNCTION_BLOCK

PROGRAM main
  VAR_INPUT
    run_it : BOOL;
    inc   : INT;
  END_VAR
  VAR_OUTPUT
    total : INT;
    done  : BOOL;
  END_VAR
  VAR
    c : COUNT;
  END_VAR
  c(EN := run_it, inc := inc);
  total := c.total;
  done  := c.ENO;
END_PROGRAM
