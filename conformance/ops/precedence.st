(* Operator precedence and associativity, with no parentheses in the
   expressions under test. *)
PROGRAM main
  VAR_INPUT
    a : INT;
    b : INT;
    c : INT;
    p : BOOL;
    q : BOOL;
    r : BOOL;
  END_VAR
  VAR_OUTPUT
    e1 : INT;
    e2 : INT;
    e3 : INT;
    e4 : INT;
    e5 : INT;
    e6 : INT;
    e7 : INT;
    l1 : BOOL;
    l2 : BOOL;
    l3 : BOOL;
    l4 : BOOL;
    l5 : BOOL;
    l6 : BOOL;
  END_VAR
  e1 := a + b * c;        (* * before + *)
  e2 := (a + b) * c;      (* parentheses *)
  e3 := a - b - c;        (* left associative *)
  e4 := a / b * c;        (* same level, left to right *)
  e5 := -a MOD b;         (* unary minus before MOD *)
  e6 := a MOD b * c;      (* same level, left to right *)
  e7 := a - -b;           (* unary minus on the right operand *)
  l1 := p OR q AND r;     (* AND before OR *)
  l2 := p XOR q OR r;     (* XOR before OR *)
  l3 := NOT p AND q;      (* NOT before AND *)
  l4 := a < b AND b < c;  (* comparison before AND *)
  l5 := a + b = c;        (* + before = *)
  l6 := NOT p = q;        (* NOT before = *)
END_PROGRAM
