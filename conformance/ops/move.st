(* MOVE returns its input unchanged, for any type (ed.3 table 22, ed.2
   table 22 feature "MOVE"; not checked against the text, see
   notes/verification.md V-06). *)
PROGRAM main
  VAR_INPUT
    i : INT;
    b : BOOL;
    k : REAL;
  END_VAR
  VAR_OUTPUT
    mi : INT;
    mr : REAL;
    mb : BOOL;
    mt : TIME;
    mw : WORD;
    ms : STRING;
    mx : INT;
  END_VAR
  VAR
    r : REAL := 2.5;
    t : TIME := T#1500ms;
    w : WORD := 16#BEEF;
    s : STRING := 'move';
    arr : ARRAY[0..2] OF INT := [10, 20, 30];
  END_VAR
  mi := MOVE(i);
  mr := MOVE(r * k);
  mb := MOVE(NOT b);
  mt := MOVE(t);
  mw := MOVE(w);
  ms := MOVE(s);
  mx := MOVE(IN := arr[1]);
END_PROGRAM
