(* Whether AND and OR evaluate their right operand when the left one
   already decides the result: "Boolean expressions may be evaluated only
   as far as necessary to determine the resultant value" (ed.3 7.3.2 /
   ed.2 3.3.1), so both behaviours are allowed. Observed through a
   function that counts its calls in a VAR_IN_OUT variable. *)
FUNCTION TICK : BOOL
  VAR_IN_OUT
    n : INT;
  END_VAR
  n := n + 1;
  TICK := TRUE;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    g : BOOL;
  END_VAR
  VAR_OUTPUT
    a     : BOOL;   (* g AND TICK() *)
    o     : BOOL;   (* g OR TICK() *)
    n_and : INT;    (* 1 if TICK was called for a, else 0 *)
    n_or  : INT;    (* 1 if TICK was called for o, else 0 *)
  END_VAR
  VAR
    na : INT;
    no : INT;
  END_VAR
  na := 0;
  no := 0;
  a := g AND TICK(n := na);
  o := g OR TICK(n := no);
  n_and := na;
  n_or  := no;
END_PROGRAM
