(* Duration literals with a millisecond part. A TIME literal denotes an
   exact duration (ed.3 6.3.4); a conversion that computes the seconds in
   binary floating point and truncates loses a nanosecond on about half of
   the millisecond values, which then reads one millisecond short. Found
   by tools/fuzz (profile time, OpenPLC's matiec on x86-64). *)
PROGRAM main
  VAR_OUTPUT
    t1 : TIME;
    t2 : TIME;
    t3 : TIME;
    t4 : TIME;
    t5 : TIME;
  END_VAR
  t1 := T#4748ms;
  t2 := T#3496ms;
  t3 := T#4ms;
  t4 := T#4s219ms;
  t5 := T#1263ms;
END_PROGRAM
