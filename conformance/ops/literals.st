(* Integer literal forms: based, with underscores, typed, negated. *)
PROGRAM main
  VAR_OUTPUT
    hex   : INT;
    bin   : INT;
    oct   : INT;
    under : DINT;
    typed : INT;
    neg   : INT;
    tu    : UINT;
    dh    : DINT;
  END_VAR
  hex   := 16#FF;
  bin   := 2#1010_1010;
  oct   := 8#17;
  under := 1_000_000;
  typed := INT#-5;
  neg   := -16#10;
  tu    := UINT#65535;
  dh    := DINT#16#7FFF_FFFF;
END_PROGRAM
