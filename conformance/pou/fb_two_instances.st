(* One user-defined function block, two instances with independent state. *)
FUNCTION_BLOCK ACCUM
  VAR_INPUT
    enable  : BOOL;
    inc : DINT;
  END_VAR
  VAR_OUTPUT
    total : DINT;
    calls : INT;
  END_VAR
  VAR
    enabled_calls : INT;
  END_VAR
  calls := calls + 1;
  IF enable THEN
    total := total + inc;
    enabled_calls := enabled_calls + 1;
  END_IF;
END_FUNCTION_BLOCK

PROGRAM main
  VAR_INPUT
    enable_a  : BOOL;
    inc_a : DINT;
    enable_b  : BOOL;
    inc_b : DINT;
  END_VAR
  VAR_OUTPUT
    tot_a   : DINT;
    tot_b   : DINT;
    calls_a : INT;
    calls_b : INT;
  END_VAR
  VAR
    a : ACCUM;
    b : ACCUM;
  END_VAR
  a(enable := enable_a, inc := inc_a);
  b(enable := enable_b, inc := inc_b, total => tot_b, calls => calls_b);
  tot_a := a.total;
  calls_a := a.calls;
END_PROGRAM
