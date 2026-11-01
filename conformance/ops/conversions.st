(* Typed conversion functions between INT, DINT and UINT, with values in
   range of the target type. *)
PROGRAM main
  VAR_INPUT
    i  : INT;    (* any INT, to DINT *)
    ip : INT;    (* 0..32767, to UINT *)
    d  : DINT;   (* -32768..32767, to INT *)
    dp : DINT;   (* 0..65535, to UINT *)
    u  : UINT;   (* 0..32767, to INT *)
    ub : UINT;   (* any UINT, to DINT *)
  END_VAR
  VAR_OUTPUT
    i2d : DINT;
    i2u : UINT;
    d2i : INT;
    d2u : UINT;
    u2i : INT;
    u2d : DINT;
  END_VAR
  i2d := INT_TO_DINT(i);
  i2u := INT_TO_UINT(ip);
  d2i := DINT_TO_INT(d);
  d2u := DINT_TO_UINT(dp);
  u2i := UINT_TO_INT(u);
  u2d := UINT_TO_DINT(ub);
END_PROGRAM
