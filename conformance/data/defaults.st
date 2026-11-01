(* Default initial values of variables declared without one: 0 for the
   numeric types, FALSE, T#0s, the empty string, the first enumerator of an
   enumeration, the lower limit of a subrange, and element-wise for arrays
   and structures (ed.3 6.4.4.4 and table 10 / ed.2 2.3.3.1 table 10 and
   2.4.2). The program never writes the output variables it reports. *)
TYPE
  COLOR : (RED, GREEN, BLUE);
  SMALL : INT (5..10);
  PAIR : STRUCT
    a : INT;
    b : BOOL;
  END_STRUCT;
END_TYPE

PROGRAM main
  VAR_OUTPUT
    b  : BOOL;
    i  : INT;
    d  : DINT;
    u  : UINT;
    bt : BYTE;
    w  : WORD;
    dw : DWORD;
    r  : REAL;
    lr : LREAL;
    t  : TIME;
    s  : STRING;
    slen   : INT;    (* LEN(s) *)
    is_red : BOOL;   (* c = RED *)
    lo_lim : INT;    (* the subrange variable *)
    arr    : INT;    (* v[0] + v[1] + v[2] *)
    pa     : INT;    (* p.a *)
    pb     : BOOL;   (* p.b *)
  END_VAR
  VAR
    c  : COLOR;
    sm : SMALL;
    v  : ARRAY[0..2] OF INT;
    p  : PAIR;
  END_VAR
  slen   := LEN(s);
  is_red := c = RED;
  lo_lim := sm;
  arr    := v[0] + v[1] + v[2];
  pa     := p.a;
  pb     := p.b;
END_PROGRAM
