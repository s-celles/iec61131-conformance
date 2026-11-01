(* Integer division and modulo by zero. *)
PROGRAM main
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    q : INT;
    m : INT;
  END_VAR
  q := a / b;
  m := a MOD b;
END_PROGRAM
