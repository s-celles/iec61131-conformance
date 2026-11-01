(* Array initialisers: a list, a repetition factor, and the default. *)
PROGRAM main
  VAR_OUTPUT
    s_list : INT;
    s_rep  : INT;
    z      : INT;
    f      : BOOL;
  END_VAR
  VAR
    lst   : ARRAY[1..3] OF INT := [7, 8, 9];
    rep   : ARRAY[0..3] OF INT := [4(5)];
    zero  : ARRAY[0..1] OF INT;
    flags : ARRAY[0..2] OF BOOL := [TRUE, FALSE, TRUE];
  END_VAR
  s_list := lst[1] + lst[2] + lst[3];
  s_rep  := rep[0] + rep[1] + rep[2] + rep[3];
  z      := zero[0] + zero[1];
  f      := flags[0] AND NOT flags[1] AND flags[2];
END_PROGRAM
