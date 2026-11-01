(* Standard character string functions, positional arguments. *)
PROGRAM main
  VAR_INPUT
    n : INT;    (* 1..4 *)
  END_VAR
  VAR_OUTPUT
    o_len     : INT;
    o_concat  : STRING;
    o_left    : STRING;
    o_right   : STRING;
    o_mid     : STRING;
    o_insert  : STRING;
    o_delete  : STRING;
    o_replace : STRING;
    o_find    : INT;
    o_find0   : INT;
  END_VAR
  o_len     := LEN('hello');
  o_concat  := CONCAT('ab', 'cd');
  o_left    := LEFT('hello', n);              (* L := n *)
  o_right   := RIGHT('hello', n);             (* L := n *)
  o_mid     := MID('hello', n, 2);            (* L := n, P := 2 *)
  o_insert  := INSERT('hello', 'XX', n);      (* after character P := n *)
  o_delete  := DELETE('hello', n, 2);         (* L := n from P := 2 *)
  o_replace := REPLACE('hello', 'YY', n, 2);  (* L := n at P := 2 *)
  o_find    := FIND('hello', 'll');
  o_find0   := FIND('hello', 'zz');
END_PROGRAM
