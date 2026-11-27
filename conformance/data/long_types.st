(* The 64-bit elementary types LINT, ULINT and LWORD: their ranges,
   arithmetic beyond 32 bits, and LWORD shifts, rotations and conversion
   to DWORD (ed.3 table 10, ed.2 table 10; not checked against the text,
   see notes/verification.md V-04). The harness reads 32-bit scalars, so
   the 64-bit results are exposed as DWORD halves, DINT or BOOL. *)
PROGRAM main
  VAR_OUTPUT
    max_ok : BOOL;
    min_ok : BOOL;
    u_ok : BOOL;
    p_div : DINT;
    w_hi : DWORD;
    w_lo : DWORD;
    r_hi : DWORD;
    r_lo : DWORD;
  END_VAR
  VAR
    big : LINT := 9223372036854775807;
    small : LINT;
    u : ULINT := 18446744073709551615;
    p : LINT;
    w : LWORD := 16#0123456789ABCDEF;
    r : LWORD;
  END_VAR
  small := -big - 1;
  max_ok := big > LINT#2147483647 AND big - 1 = LINT#9223372036854775806;
  min_ok := small < LINT#0 AND small + big = LINT#-1;
  u_ok := u > ULINT#9223372036854775807 AND u - ULINT#1 = ULINT#18446744073709551614;
  p := LINT#4000000000 * LINT#3;
  p_div := LINT_TO_DINT(p / LINT#1000);
  w_hi := LWORD_TO_DWORD(SHR(w, 32));
  w_lo := LWORD_TO_DWORD(w);
  r := ROL(LWORD#16#8000000000000001, 1);
  r_hi := LWORD_TO_DWORD(SHR(r, 32));
  r_lo := LWORD_TO_DWORD(r);
END_PROGRAM
