(* EN and ENO on a function block, declared by the user as ed.2 2.5.2.1a
   and ed.3 6.6.1.5 give them: with EN FALSE the body is not executed and
   ENO is FALSE. ENO is read through the call (ENO => done), the only use
   ed.3 6.6.1.5 rule 6 allows (issue #16). *)
FUNCTION_BLOCK COUNT
  VAR_INPUT
    EN  : BOOL := TRUE;
    inc : INT;
  END_VAR
  VAR_OUTPUT
    ENO   : BOOL;
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
  c(EN := run_it, inc := inc, ENO => done);
  total := c.total;
END_PROGRAM
