(* Exponentiation: the EXPT function and the ** operator. *)
PROGRAM main
  VAR_INPUT
    x : REAL;
    n : INT;
  END_VAR
  VAR_OUTPUT
    o_expt : REAL;
    o_pow2 : REAL;
  END_VAR
  o_expt := EXPT(x, n);
  o_pow2 := x ** 2;
END_PROGRAM
