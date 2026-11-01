(* A FUNCTION_BLOCK's VAR_TEMP section is initialised at every invocation:
   t starts from 0 on each call, so y depends on this call's input only. *)
FUNCTION_BLOCK TMP
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    y : INT;
  END_VAR
  VAR_TEMP
    t : INT;
  END_VAR
  t := t + x;
  y := t;
END_FUNCTION_BLOCK

PROGRAM main
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    y : INT;
  END_VAR
  VAR
    fb : TMP;
  END_VAR
  fb(x := x);
  y := fb.y;
END_PROGRAM
