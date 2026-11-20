(* BCD conversions: WORD_BCD_TO_UINT reads each hexadecimal digit of a
   WORD as a decimal digit, UINT_TO_BCD_WORD writes a number as one
   decimal digit per nibble (ed.3 table 22; ed.2 table 22 has the
   generic BCD_TO_INT and INT_TO_BCD; names and numbers not checked
   against the text, see notes/verification.md V-05). *)
PROGRAM main
  VAR_INPUT
    n : UINT;
    w : WORD;
  END_VAR
  VAR_OUTPUT
    to_bcd : WORD;
    from_bcd : UINT;
    round_trip : UINT;
  END_VAR
  to_bcd := UINT_TO_BCD_WORD(n);
  from_bcd := WORD_BCD_TO_UINT(w);
  round_trip := WORD_BCD_TO_UINT(UINT_TO_BCD_WORD(n));
END_PROGRAM
