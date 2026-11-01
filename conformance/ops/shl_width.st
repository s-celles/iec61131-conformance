(* The result of SHL has the width of its input: the bits shifted out on
   the left are lost, which shows when the result is shifted back or
   rotated (ed.3 table 30 / ed.2 table 25: SHL "shift left by N bits,
   zero-filled on the right"). ops/bit_ops checks each function alone;
   this composes them. Found by tools/fuzz. *)
PROGRAM main
  VAR_INPUT
    b : BYTE;
    w : WORD;
  END_VAR
  VAR_OUTPUT
    b_back : BYTE;   (* SHR(SHL(b, 7), 4): only bit 0 of b can survive, at bit 3 *)
    b_rol  : BYTE;   (* ROL(SHL(b, 4), 4): the low nibble of b, at bits 0..3 *)
    w_back : WORD;   (* SHR(SHL(w, 12), 8): bits 0..3 of w, at bits 4..7 *)
    w_ror  : WORD;   (* ROR(SHL(w, 8), 8): the low byte of w *)
    b_or   : BYTE;   (* 16#44 OR SHR(SHL(b, 7), 4) *)
  END_VAR
  b_back := SHR(SHL(b, 7), 4);
  b_rol  := ROL(SHL(b, 4), 4);
  w_back := SHR(SHL(w, 12), 8);
  w_ror  := ROR(SHL(w, 8), 8);
  b_or   := BYTE#16#44 OR SHR(SHL(b, 7), 4);
END_PROGRAM
