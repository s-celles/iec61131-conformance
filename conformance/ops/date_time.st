(* DATE, TIME_OF_DAY and DATE_AND_TIME: literals, the arithmetic of ed.3
   table 30 (ed.2 table 30: DATE - DATE, TOD +/- TIME, TOD - TOD,
   DT +/- TIME, DT - DT), comparison, and the conversions DT_TO_DATE and
   DT_TO_TOD, all observed through TIME and BOOL outputs. *)
PROGRAM main
  VAR_OUTPUT
    d_sub   : TIME;  (* DATE - DATE *)
    tod_sub : TIME;  (* TOD - TOD *)
    dt_sub  : TIME;  (* DT - DT *)
    tod_add : TIME;  (* (TOD + TIME) - TOD *)
    tod_min : TIME;  (* (TOD - TIME) - TOD *)
    dt_add  : TIME;  (* (DT + TIME) - DT *)
    dt_min  : TIME;  (* (DT - TIME) - DT, across a leap day *)
    same_d  : BOOL;  (* DT_TO_DATE(dt1) = d1 *)
    same_t  : BOOL;  (* DT_TO_TOD(dt1) = t1 *)
    before  : BOOL;  (* dt2 < dt1 *)
  END_VAR
  VAR
    d1  : DATE := D#2024-03-01;
    d2  : DATE := D#2024-02-27;
    t1  : TOD  := TOD#12:30:00;
    t2  : TOD  := TOD#10:15:30.5;
    dt1 : DT   := DT#2024-03-01-12:30:00;
    dt2 : DT   := DT#2024-02-29-23:59:59;
  END_VAR
  d_sub   := d1 - d2;
  tod_sub := t1 - t2;
  dt_sub  := dt1 - dt2;
  tod_add := (TOD#12:00:00 + T#90m) - TOD#00:00:00;
  tod_min := (TOD#01:00:00 - T#30m) - TOD#00:00:00;
  dt_add  := (DT#2024-02-28-23:00:00 + T#2h) - DT#2024-02-28-00:00:00;
  dt_min  := (DT#2024-03-01-00:30:00 - T#1h) - DT#2024-02-29-00:00:00;
  same_d  := DT_TO_DATE(dt1) = d1;
  same_t  := DT_TO_TOD(dt1) = t1;
  before  := dt2 < dt1;
END_PROGRAM
