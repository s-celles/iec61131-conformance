(* Integer division and MOD with negative operands: the quotient of two
   integers is truncated toward zero, and MOD is defined by
   IN1 - (IN1 / IN2) * IN2, so its result takes the sign of IN1 (ed.3
   table 29, ed.2 table 24; not checked against the text, see
   notes/verification.md V-03). *)
PROGRAM main
  VAR_INPUT
    a : INT;
    b : INT;
    ad : DINT;
    bd : DINT;
  END_VAR
  VAR_OUTPUT
    q : INT;
    m : INT;
    qd : DINT;
    md : DINT;
  END_VAR
  q := a / b;
  m := a MOD b;
  qd := ad / bd;
  md := ad MOD bd;
END_PROGRAM
