(* Multi-dimensional arrays: ARRAY[0..1, 0..2] with a flat initialiser
   (rightmost subscript varying fastest) and an array of a named array type
   with a nested initialiser; element access and loops over one subscript. *)
TYPE
  ROW : ARRAY[0..2] OF INT;
END_TYPE

PROGRAM main
  VAR_INPUT
    i : INT;   (* 0..1 *)
    j : INT;   (* 0..2 *)
  END_VAR
  VAR_OUTPUT
    m_ij : INT;
    a_ij : INT;
    rsum : INT;   (* sum of m[i, 0..2] *)
    csum : INT;   (* sum of a[0..1][j] *)
  END_VAR
  VAR
    m : ARRAY[0..1, 0..2] OF INT := [1, 2, 3, 4, 5, 6];
    a : ARRAY[0..1] OF ROW := [[10, 20, 30], [40, 50, 60]];
    k : INT;
  END_VAR
  m_ij := m[i, j];
  a_ij := a[i][j];
  rsum := 0;
  FOR k := 0 TO 2 DO
    rsum := rsum + m[i, k];
  END_FOR;
  csum := 0;
  FOR k := 0 TO 1 DO
    csum := csum + a[k][j];
  END_FOR;
END_PROGRAM
