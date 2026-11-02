(* MUX over types other than INT: MUX is declared on ANY (ed.3 table 32,
   ed.2 table 27), so the inputs may be UINT, BYTE, WORD, BOOL or
   TIME, the selector staying an INT. ops/std_functions only uses INT
   inputs. Found while fuzzing rk. *)
PROGRAM main
  VAR_INPUT
    k : INT;   (* 0..2 *)
  END_VAR
  VAR_OUTPUT
    mu : UINT;
    mb : BYTE;
    mw : WORD;
    mx : BOOL;
    mt : TIME;
  END_VAR
  VAR
    u0 : UINT := 10;
    u1 : UINT := 65535;
    u2 : UINT := 7;
    b0 : BYTE := 16#0F;
    b1 : BYTE := 16#F0;
    b2 : BYTE := 16#AA;
    w0 : WORD := 16#1234;
    w1 : WORD := 16#FFFF;
    w2 : WORD := 16#0000;
    t0 : TIME := T#1s;
    t1 : TIME := T#250ms;
    t2 : TIME := T#0s;
  END_VAR
  mu := MUX(k, u0, u1, u2);
  mb := MUX(k, b0, b1, b2);
  mw := MUX(k, w0, w1, w2);
  mx := MUX(k, TRUE, FALSE, TRUE);
  mt := MUX(k, t0, t1, t2);
END_PROGRAM
