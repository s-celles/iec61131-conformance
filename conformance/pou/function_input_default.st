(* An input of a function that is not assigned in a formal call takes its
   declared initial value (ed.3 6.6.1.7.1: in a formal call, inputs may be
   omitted and keep their initial value; 6.4.4.4 initial values). *)
FUNCTION SCALE : INT
  VAR_INPUT
    x   : INT;
    k   : INT := 3;
    off : INT := -1;
  END_VAR
  SCALE := x * k + off;
END_FUNCTION

PROGRAM main
  VAR_INPUT
    x : INT;
  END_VAR
  VAR_OUTPUT
    dflt   : INT;   (* k and off omitted *)
    with_k : INT;   (* off omitted *)
    all    : INT;   (* all given *)
  END_VAR
  dflt   := SCALE(x := x);
  with_k := SCALE(x := x, k := 10);
  all    := SCALE(x := x, k := 2, off := 5);
END_PROGRAM
