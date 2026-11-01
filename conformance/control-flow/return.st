(* RETURN leaves the body of a function block or a function early
   (ed.3 7.3.3.3.4 table 72 / ed.2 3.3.2.3 table 56). The statements after
   it are not executed; a function returns the value its name holds at
   that point. *)
FUNCTION_BLOCK GUARD
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    y     : INT;
    calls : INT;
  END_VAR
  calls := calls + 1;
  IF x < 0 THEN
    RETURN;
  END_IF;
  y := x * 2;
END_FUNCTION_BLOCK

FUNCTION CLAMP10 : INT
  VAR_INPUT
    v : INT;
  END_VAR
  CLAMP10 := v;
  IF v > 10 THEN
    CLAMP10 := 10;
    RETURN;
  END_IF;
  CLAMP10 := CLAMP10 + 100;   (* not reached when v > 10 *)
END_FUNCTION

PROGRAM main
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    y     : INT;
    calls : INT;
    c     : INT;
  END_VAR
  VAR
    g : GUARD;
  END_VAR
  g(x := x);
  y     := g.y;
  calls := g.calls;
  c     := CLAMP10(x);
END_PROGRAM
