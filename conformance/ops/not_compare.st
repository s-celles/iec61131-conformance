(* NOT on a BYTE or WORD variable inside a comparison. NOT yields a value
   of the operand's bit-string type (ed.3 table 33), so NOT 16#00 is the
   BYTE 16#FF whether it is stored first or compared directly. Found by
   tools/fuzz (profile wide, matiec and the OpenPLC fork). *)
PROGRAM main
  VAR_OUTPUT
    q1 : BOOL;
    q2 : BOOL;
    q3 : BOOL;
    q4 : BOOL;
  END_VAR
  VAR
    b : BYTE := 16#00;
    c : BYTE := 16#FF;
    w : WORD := 16#0F0F;
    x : WORD := 16#F0F0;
  END_VAR
  q1 := (NOT b) = c;
  q2 := (NOT b) <> c;
  q3 := (NOT w) = x;
  q4 := (NOT w) <> x;
END_PROGRAM
