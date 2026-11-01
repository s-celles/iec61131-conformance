(* LIMIT when MN > MX. The standard defines LIMIT by a formula,
   MIN(MAX(IN, MN), MX) (ed.3 table 32 / ed.2 table 27), which gives MX
   whenever IN >= MX or MN >= MX, so the upper limit wins over an inverted
   lower one. ops/std_functions keeps MN <= MX; this test is the other
   case, found by tools/fuzz. *)
PROGRAM main
  VAR_INPUT
    mn : INT;
    x  : INT;
    mx : INT;
  END_VAR
  VAR_OUTPUT
    l : INT;
  END_VAR
  l := LIMIT(mn, x, mx);
END_PROGRAM
