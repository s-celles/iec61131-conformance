(* Extensible comparison functions: GT, GE, EQ, LE and LT take more than
   two inputs, and the result is the conjunction of the comparisons of
   each input with the next, GT(a, b, c) = (a > b) AND (b > c) (ed.3
   table 28, ed.2 table 28; not checked against the text, see
   notes/verification.md V-02). *)
PROGRAM main
  VAR_OUTPUT
    q1 : BOOL;
    q2 : BOOL;
    q3 : BOOL;
    q4 : BOOL;
    q5 : BOOL;
    q6 : BOOL;
    q7 : BOOL;
    q8 : BOOL;
  END_VAR
  VAR
    a : INT := 3;
    b : INT := 2;
    c : INT := 1;
    d : INT := 4;
    e : INT := 5;
    f : INT := 6;
  END_VAR
  q1 := GT(a, b, c);
  q2 := GT(a, c, b);
  q3 := GE(a, a, c);
  q4 := EQ(e, e, e);
  q5 := EQ(e, e, f);
  q6 := LT(c, b, a);
  q7 := LE(c, a, b);
  q8 := GT(d, c, a);
END_PROGRAM
