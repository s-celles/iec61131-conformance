(* INSERT on variables, so literal-argument code generation cannot hide
   whether P denotes the character after which to insert. *)
PROGRAM main
  VAR_INPUT
    pos : INT;
  END_VAR
  VAR_OUTPUT
    inserted : STRING;
  END_VAR
  VAR
    src : STRING := 'abcde';
    part : STRING := 'XY';
  END_VAR
  inserted := INSERT(src, part, pos);
END_PROGRAM
