(* ABS and negation of the most negative value of INT and DINT. *)
PROGRAM main
  VAR_INPUT
    x : INT;
    d : DINT;
  END_VAR
  VAR_OUTPUT
    ax : INT;
    nx : INT;
    ad : DINT;
    nd : DINT;
  END_VAR
  ax := ABS(x);
  nx := -x;
  ad := ABS(d);
  nd := -d;
END_PROGRAM
