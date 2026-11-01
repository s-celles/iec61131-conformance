(* Based literals in a bit-string context. An untyped based literal
   (16#A5, 2#1010_0101) takes the type of its context (ed.3 6.3.2 table 5
   features 4-6, ed.2 2.2.1 table 2), so it can be assigned to a BYTE or
   WORD, combined with one by AND / OR / XOR, passed to SHL, and compared;
   the typed form (BYTE#16#A5, WORD#16#00FF) is feature 9 of the same
   table. ops/bit_ops computes with variables only; this is the literal
   spelling, found by tools/fuzz. *)
PROGRAM main
  VAR_INPUT
    b : BYTE;
    w : WORD;
    n : INT;
  END_VAR
  VAR_OUTPUT
    ob   : BYTE;   (* 16#A5 *)
    ow   : WORD;   (* 2#1000_0000_0000_0001 *)
    b_and : BYTE;  (* b AND 16#0F *)
    w_or  : WORD;  (* w OR 16#FF00 *)
    b_xor : BYTE;  (* b XOR BYTE#16#FF *)
    w_shl : WORD;  (* SHL(16#0001, n) *)
    lo55 : BOOL;   (* (w AND 16#00FF) = 16#0055 *)
    tw   : BOOL;   (* WORD#16#1234 = w *)
  END_VAR
  ob    := 16#A5;
  ow    := 2#1000_0000_0000_0001;
  b_and := b AND 16#0F;
  w_or  := w OR 16#FF00;
  b_xor := b XOR BYTE#16#FF;
  w_shl := SHL(16#0001, n);
  lo55  := (w AND 16#00FF) = 16#0055;
  tw    := WORD#16#1234 = w;
END_PROGRAM
