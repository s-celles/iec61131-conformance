(* Bitwise operators on BYTE and bit-shift functions on WORD and DWORD. *)
PROGRAM main
  VAR_INPUT
    b : BYTE;
    m : BYTE;
    w : WORD;
    d : DWORD;
    n : INT;
  END_VAR
  VAR_OUTPUT
    o_and : BYTE;
    o_or  : BYTE;
    o_xor : BYTE;
    o_not : BYTE;
    w_shl : WORD;
    w_shr : WORD;
    w_rol : WORD;
    w_ror : WORD;
    d_shl : DWORD;
    d_shr : DWORD;
    d_rol : DWORD;
    d_ror : DWORD;
  END_VAR
  o_and := b AND m;
  o_or  := b OR m;
  o_xor := b XOR m;
  o_not := NOT b;
  w_shl := SHL(w, n);
  w_shr := SHR(w, n);
  w_rol := ROL(w, n);
  w_ror := ROR(w, n);
  d_shl := SHL(d, n);
  d_shr := SHR(d, n);
  d_rol := ROL(d, n);
  d_ror := ROR(d, n);
END_PROGRAM
