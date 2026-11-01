(* TIME addition, subtraction, comparison, and duration literals. *)
PROGRAM main
  VAR_INPUT
    t1 : TIME;
    t2 : TIME;    (* records keep t2 <= t1 so t1 - t2 is not negative *)
  END_VAR
  VAR_OUTPUT
    sum  : TIME;
    diff : TIME;
    is_lt : BOOL;
    is_gt : BOOL;
    is_le : BOOL;
    is_eq : BOOL;
    lit1 : TIME;
    lit2 : TIME;
    lit3 : TIME;
    lit4 : TIME;
    lit5 : TIME;
  END_VAR
  sum  := t1 + t2;
  diff := t1 - t2;
  is_lt := t1 < t2;
  is_gt := t1 > t2;
  is_le := t1 <= t2;
  is_eq := t1 = t2;
  lit1 := T#1m30s;
  lit2 := T#1h2m3s4ms;
  lit3 := T#1.5s;
  lit4 := TIME#500ms;
  lit5 := T#2d;
END_PROGRAM
