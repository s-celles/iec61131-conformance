(* VAR_IN_OUT: a function block and a function operate on the caller's
   variable itself, so what they write is visible to the caller after the
   call (ed.3 6.6.2.3 / ed.2 2.5.2.2 and 2.5.1.3). *)
FUNCTION_BLOCK ADDER
  VAR_INPUT
    inc : INT;
  END_VAR
  VAR_IN_OUT
    acc : INT;
  END_VAR
  acc := acc + inc;
END_FUNCTION_BLOCK

FUNCTION SWAP : BOOL
  VAR_IN_OUT
    a : INT;
    b : INT;
  END_VAR
  VAR
    tmp : INT;
  END_VAR
  tmp := a;
  a := b;
  b := tmp;
  SWAP := TRUE;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    inc : INT;
  END_VAR
  VAR_OUTPUT
    total : INT;   (* passed as acc, accumulates across cycles *)
    p     : INT;   (* x after the swap *)
    q     : INT;   (* y after the swap *)
    ok    : BOOL;
  END_VAR
  VAR
    add_fb : ADDER;
    x     : INT := 1;
    y     : INT := 2;
  END_VAR
  add_fb(inc := inc, acc := total);
  ok := SWAP(a := x, b := y);
  p := x;
  q := y;
END_PROGRAM
