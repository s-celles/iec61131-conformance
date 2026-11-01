(* A function with VAR_OUTPUT variables besides its return value
   (ed.3 6.6.1.3 / ed.2 2.5.1.3), read back with the "=>" syntax of a
   formal call. *)
FUNCTION DIVMOD : BOOL
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    q : INT;
    r : INT;
  END_VAR
  IF b = 0 THEN
    q := 0;
    r := 0;
    DIVMOD := FALSE;
  ELSE
    q := a / b;
    r := a MOD b;
    DIVMOD := TRUE;
  END_IF;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    a : INT;
    b : INT;
  END_VAR
  VAR_OUTPUT
    ok : BOOL;
    q  : INT;
    r  : INT;
  END_VAR
  ok := DIVMOD(a := a, b := b, q => q, r => r);
END_PROGRAM
