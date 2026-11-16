(* A member initial value in a structured type, and a partial initialiser
   of a structured variable with a BOOL member, given out of declaration
   order. See struct_init.trace for the derivation. *)
TYPE
  CFG : STRUCT
    n  : INT := 5;
    flag : BOOL;
    k  : INT;
  END_STRUCT;
END_TYPE

PROGRAM main
  VAR_INPUT
    i : INT;    (* added to c.k each cycle *)
  END_VAR
  VAR_OUTPUT
    dn  : INT;
    dflag : BOOL;
    dk  : INT;
    cn  : INT;
    cflag : BOOL;
    ck  : INT;
  END_VAR
  VAR
    d : CFG;
    c : CFG := (k := 3, flag := TRUE);
  END_VAR
  c.k := c.k + i;
  dn := d.n;
  dflag := d.flag;
  dk := d.k;
  cn := c.n;
  cflag := c.flag;
  ck := c.k;
END_PROGRAM
