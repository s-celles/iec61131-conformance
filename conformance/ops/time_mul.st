(* TIME multiplied by an integer (ed.3 table 30 MUL: TIME * ANY_NUM ->
   TIME; ed.2 table 24), with products whose millisecond part times the
   factor exceeds 2^31 nanoseconds, where an implementation that scales
   seconds and nanoseconds separately in 32-bit arithmetic goes wrong.
   ops/time_arith multiplies small values only. Found by tools/fuzz. *)
PROGRAM main
  VAR_INPUT
    t : TIME;
    n : INT;
  END_VAR
  VAR_OUTPUT
    p    : TIME;   (* t * n *)
    p4   : TIME;   (* T#700ms * 4 *)
    p44  : TIME;   (* T#71s487ms * 44 *)
    back : BOOL;   (* (t * n) - t = t * (n - 1) *)
  END_VAR
  p    := t * n;
  p4   := T#700ms * 4;
  p44  := T#71s487ms * 44;
  back := (t * n) - t = t * (n - 1);
END_PROGRAM
