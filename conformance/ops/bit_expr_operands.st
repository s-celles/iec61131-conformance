(* Bit-string NOT and the shift / rotate functions applied to expressions
   rather than to variables: NOT (a XOR b), SHL(a OR b, n), ROL(a XOR
   BYTE#16#0F, n), and a comparison of two such results. ops/bit_ops
   applies them to variables only; this is the other spelling, found by
   tools/fuzz. *)
PROGRAM main
  VAR_INPUT
    a : BYTE;
    b : BYTE;
    w : WORD;
    n : INT;   (* 0..7 *)
  END_VAR
  VAR_OUTPUT
    n_xor : BYTE;   (* NOT (a XOR b) *)
    n_and : WORD;   (* NOT (w AND WORD#16#00FF) *)
    s_or  : BYTE;   (* SHL(a OR b, n) *)
    r_xor : BYTE;   (* ROL(a XOR BYTE#16#0F, n) *)
    r_w   : WORD;   (* ROR(NOT w, n) *)
    same  : BOOL;   (* (a AND b) = (NOT (NOT a OR NOT b)) *)
  END_VAR
  n_xor := NOT (a XOR b);
  n_and := NOT (w AND WORD#16#00FF);
  s_or  := SHL(a OR b, n);
  r_xor := ROL(a XOR BYTE#16#0F, n);
  r_w   := ROR(NOT w, n);
  same  := (a AND b) = (NOT (NOT a OR NOT b));
END_PROGRAM
