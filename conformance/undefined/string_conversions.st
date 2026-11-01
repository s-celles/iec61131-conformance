(* Conversions between integers and strings. *)
PROGRAM main
  VAR_INPUT
    i : INT;
  END_VAR
  VAR_OUTPUT
    s_i  : STRING;
    back : INT;
    s_d  : STRING;
  END_VAR
  s_i  := INT_TO_STRING(i);
  back := STRING_TO_INT('42');
  s_d  := DINT_TO_STRING(DINT#-2147483648);
END_PROGRAM
