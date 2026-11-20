(* Edge-detecting inputs of a function block: VAR_INPUT r : BOOL R_EDGE
   reads TRUE at an invocation where the actual input is TRUE and was
   FALSE at the previous invocation, F_EDGE the converse, as if an
   R_TRIG / F_TRIG instance were applied to the input (ed.2 2.5.2.2,
   ed.3 to locate; not checked against the text, see
   notes/verification.md V-01). *)
FUNCTION_BLOCK EDGES
  VAR_INPUT
    r : BOOL R_EDGE;
    f : BOOL F_EDGE;
  END_VAR
  VAR_OUTPUT
    rq : BOOL;
    fq : BOOL;
    nr : INT;
    nf : INT;
  END_VAR
  rq := r;
  fq := f;
  IF r THEN
    nr := nr + 1;
  END_IF;
  IF f THEN
    nf := nf + 1;
  END_IF;
END_FUNCTION_BLOCK

PROGRAM main
  VAR_INPUT
    x : BOOL;
  END_VAR
  VAR_OUTPUT
    rq : BOOL;
    fq : BOOL;
    nr : INT;
    nf : INT;
  END_VAR
  VAR
    e : EDGES;
  END_VAR
  e(r := x, f := x);
  rq := e.rq;
  fq := e.fq;
  nr := e.nr;
  nf := e.nf;
END_PROGRAM
