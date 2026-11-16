(* MUX whose selector K is itself a MUX call: K is an ANY_INT input
   (ed.3 table 32), and any expression of that type may be an input of a
   function (7.3.2), a call included. Found by tools/fuzz (RuSTy, profiles
   calls, time and strings). *)
PROGRAM main
  VAR_INPUT
    k : INT;   (* 0..2 *)
  END_VAR
  VAR_OUTPUT
    r : INT;
    u : INT;
  END_VAR
  VAR
    x0 : INT := 0;
    x1 : INT := 1;
    x2 : INT := 2;
    a : INT := 10;
    b : INT := 20;
    c : INT := 30;
  END_VAR
  r := MUX(MUX(k, x1, x2, x0), a, b, c);
  u := MUX(MUX(k, x2, x1, x0), k, b, c);
END_PROGRAM
